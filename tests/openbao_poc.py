"""Offline OpenBao/local-storage/ESO preparation; no live credentials or APIs."""

import hashlib
import json
import os
from pathlib import Path
import subprocess
import tarfile
import tempfile
import unittest

import yaml


CHART_SHA256 = "d50ed31b8305f430df308c342dd3c1efa877222380e99cb480f74f070d6beaa8"


def run(args, **kwargs):
    return subprocess.run(args, check=True, capture_output=True, text=True, **kwargs).stdout


def render(path):
    return [d for d in yaml.safe_load_all(run(["kubectl", "kustomize", str(path)])) if d]


def known_values(overrides, defaults):
    if not isinstance(defaults, dict) or not defaults:
        return
    for key, value in overrides.items():
        if key not in defaults:
            raise ValueError(f"Unknown chart value: {key}")
        if isinstance(value, dict):
            known_values(value, defaults[key])


class OpenBaoPoCTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.foundation = render("platform/openbao/foundation")
        cls.server = render("platform/openbao/server")
        cls.adapter = render("platform/openbao/eso")
        cls.bridge = render("platform/openbao")
        cls.private = render("platform/openbao/private-sync")
        cls.release = next(d for d in cls.server if d["kind"] == "HelmRelease")
        archive = Path(os.environ["OPENBAO_CHART_ARCHIVE"])
        if hashlib.sha256(archive.read_bytes()).hexdigest() != CHART_SHA256:
            raise ValueError("OpenBao chart differs from the official reviewed checksum")
        with tarfile.open(archive) as chart:
            cls.metadata = yaml.safe_load(chart.extractfile("openbao/Chart.yaml"))
            defaults = yaml.safe_load(chart.extractfile("openbao/values.yaml"))
        known_values(cls.release["spec"]["values"], defaults)
        if run(["helm", "version", "--template", "{{.Version}}"]).split("+")[0] != "v4.3.0":
            raise ValueError("Use Helm 4.3.0 for this offline render")
        chart_yaml = run([
            "helm", "template", "openbao", str(archive), "--namespace", "openbao",
            "--kube-version", "1.37.0", "--skip-tests", "--values", "-",
        ], input=yaml.safe_dump(cls.release["spec"]["values"]))
        with tempfile.TemporaryDirectory(prefix="openbao-render-") as directory:
            root = Path(directory)
            (root / "chart.yaml").write_text(chart_yaml, encoding="utf-8")
            (root / "kustomization.yaml").write_text(yaml.safe_dump({
                "apiVersion": "kustomize.config.k8s.io/v1beta1", "kind": "Kustomization",
                "resources": ["chart.yaml"],
                **cls.release["spec"]["postRenderers"][0]["kustomize"],
            }), encoding="utf-8")
            cls.chart = render(root)
        cls.sts = next(d for d in cls.chart if d["kind"] == "StatefulSet")

    def test_disconnected_and_suspended_no_backups_or_unseal_jobs(self):
        root = render("clusters/homelab")
        self.assertNotIn("openbao-foundation", {d["metadata"]["name"] for d in root})
        self.assertNotIn("backup-sync", {d["metadata"]["name"] for d in root})
        self.assertNotIn("longhorn-system", {d["metadata"]["name"] for d in root})
        self.assertIs(self.release["spec"]["suspend"], True)
        for name in ("openbao-server", "openbao-eso-poc"):
            self.assertIs(next(d for d in self.bridge if d["metadata"]["name"] == name)
                          ["spec"]["suspend"], True)
        inputs = next(d for d in self.private if d["metadata"]["name"] == "openbao-inputs"
                      and d["kind"] == "Kustomization")
        self.assertIs(inputs["spec"]["suspend"], True)
        for d in self.foundation + self.server + self.adapter + self.private + self.chart:
            self.assertNotIn(d["kind"], {"Secret", "Job", "CronJob", "Deployment", "DaemonSet",
                                         "Ingress", "HTTPRoute", "ClusterSecretStore",
                                         "UserVolumeConfig", "RawVolumeConfig"})

    def test_normal_one_member_raft_not_dev_or_cluster_secret_reader(self):
        self.assertEqual(self.metadata["version"], "0.30.3")
        self.assertEqual(self.metadata["appVersion"], "v2.7.1")
        self.assertEqual(self.sts["spec"]["replicas"], 1)
        self.assertEqual(self.sts["spec"]["updateStrategy"], {"type": "OnDelete"})
        config = next(d for d in self.chart if d["kind"] == "ConfigMap")["data"]
        hcl = "\n".join(config.values())
        self.assertIn('storage "raft"', hcl)
        self.assertIn('tls_cert_file = "/openbao/tls/tls.crt"', hcl)
        self.assertNotIn("tls_disable", hcl)
        self.assertNotIn('service_registration "kubernetes"', hcl)
        self.assertNotIn("seal ", hcl)
        self.assertNotIn("devRootToken", hcl)
        self.assertEqual({d["kind"] for d in self.chart},
                         {"ServiceAccount", "ConfigMap", "Service", "StatefulSet"})
        role = next(d for d in self.server if d["kind"] == "ClusterRole")
        self.assertEqual(role["rules"], [{"apiGroups": ["authentication.k8s.io"],
                                         "resources": ["tokenreviews"], "verbs": ["create"]}])
        for d in self.chart:
            if d["kind"] == "Service":
                self.assertEqual(d["spec"].get("type", "ClusterIP"), "ClusterIP")

    def test_actual_restricted_pod_tls_and_sealed_probe_semantics(self):
        pod = self.sts["spec"]["template"]["spec"]
        self.assertFalse(pod.get("hostNetwork", False))
        self.assertFalse(pod.get("hostPID", False))
        self.assertEqual(pod["securityContext"], {
            "runAsNonRoot": True, "runAsUser": 100, "runAsGroup": 1000,
            "fsGroup": 1000, "seccompProfile": {"type": "RuntimeDefault"},
        })
        self.assertEqual(len(pod["containers"]), 1)
        container = pod["containers"][0]
        self.assertEqual(container["image"], "quay.io/openbao/openbao:2.7.1")
        self.assertEqual(container["securityContext"], {
            "allowPrivilegeEscalation": False, "readOnlyRootFilesystem": True,
            "capabilities": {"drop": ["ALL"]},
        })
        self.assertEqual(container["readinessProbe"]["exec"]["command"],
                         ["/bin/sh", "-ec", "bao status"])
        self.assertNotIn("skip-verify", yaml.safe_dump(container))
        self.assertIn("sealedcode=204", container["livenessProbe"]["httpGet"]["path"])
        env = {e["name"]: e for e in container["env"]}
        self.assertEqual(env["BAO_CACERT"]["value"], "/openbao/tls/ca.crt")
        self.assertEqual(env["BAO_API_ADDR"]["value"], "https://openbao.openbao.svc:8200")
        self.assertFalse(any(e["name"].endswith("TOKEN") for e in container["env"]))
        mounts = {v["name"]: v for v in container["volumeMounts"]}
        self.assertIs(mounts["tls"]["readOnly"], True)
        self.assertEqual(mounts["tmp"]["mountPath"], "/tmp")
        for ns in self.foundation:
            if ns["kind"] == "Namespace":
                self.assertEqual(ns["metadata"]["labels"]["pod-security.kubernetes.io/enforce"],
                                 "restricted")

    def test_retained_prebound_directory_volume_not_default_or_quota(self):
        sc = next(d for d in self.foundation if d["kind"] == "StorageClass")
        self.assertEqual(sc["provisioner"], "kubernetes.io/no-provisioner")
        self.assertEqual(sc["volumeBindingMode"], "WaitForFirstConsumer")
        self.assertEqual(sc["reclaimPolicy"], "Retain")
        self.assertEqual(sc["metadata"]["annotations"]["storageclass.kubernetes.io/is-default-class"],
                         "false")
        pv = next(d for d in self.server if d["kind"] == "PersistentVolume")
        self.assertEqual(pv["spec"]["local"], {"path": "/var/mnt/openbao-poc"})
        self.assertEqual(pv["spec"]["claimRef"], {"namespace": "openbao", "name": "data-openbao-0"})
        self.assertEqual(pv["spec"]["persistentVolumeReclaimPolicy"], "Retain")
        expression, = pv["spec"]["nodeAffinity"]["required"]["nodeSelectorTerms"][0]["matchExpressions"]
        self.assertEqual(expression["values"], ["${OPENBAO_STORAGE_NODE}"])
        self.assertEqual(len(self.sts["spec"]["volumeClaimTemplates"]), 1)
        claim = self.sts["spec"]["volumeClaimTemplates"][0]
        self.assertEqual(claim["metadata"]["name"], "data")
        self.assertEqual(claim["spec"]["storageClassName"], "openbao-local")
        self.assertEqual(claim["spec"]["resources"]["requests"]["storage"], "2Gi")
        self.assertEqual(self.sts["spec"]["persistentVolumeClaimRetentionPolicy"],
                         {"whenDeleted": "Retain", "whenScaled": "Retain"})

    def test_bounded_eso_identity_auth_and_policy(self):
        store = next(d for d in self.adapter if d["kind"] == "SecretStore")
        self.assertEqual(store["metadata"]["namespace"], "external-secrets")
        provider = store["spec"]["provider"]["vault"]
        self.assertEqual(provider["server"], "https://openbao.openbao.svc:8200")
        self.assertNotIn("tokenSecretRef", provider["auth"])
        auth = provider["auth"]["kubernetes"]
        self.assertEqual(auth["serviceAccountRef"],
                         {"name": "eso-openbao-poc", "audiences": ["openbao-poc"]})
        role = next(d for d in self.adapter if d["kind"] == "Role")
        self.assertEqual(role["rules"], [{"apiGroups": [""], "resources": ["serviceaccounts/token"],
                                         "resourceNames": ["eso-openbao-poc"], "verbs": ["create"]}])
        bao_role = json.loads(Path("platform/openbao/configuration/eso-poc-role.json").read_text())
        self.assertEqual(bao_role["bound_service_account_names"], ["eso-openbao-poc"])
        self.assertEqual(bao_role["bound_service_account_namespaces"], ["external-secrets"])
        self.assertIs(bao_role["token_no_default_policy"], True)
        acl = Path("platform/openbao/configuration/eso-poc-policy.hcl").read_text()
        self.assertNotIn("*", acl)
        self.assertIn('path "kv/data/poc/eso-demo"', acl)
        self.assertIn('capabilities = ["read"]', acl)

    def test_network_boundaries_and_private_source_no_control_files(self):
        for d in self.server + self.adapter:
            if d["kind"] == "CiliumNetworkPolicy":
                serialized = yaml.safe_dump(d["spec"])
                self.assertNotIn("world", serialized)
                self.assertNotIn("0.0.0.0/0", serialized)
                self.assertNotIn("toFQDNs", serialized)
        source = next(d for d in self.private if d["kind"] == "GitRepository")
        self.assertEqual(source["spec"]["secretRef"], {"name": "flux-private-repo"})
        self.assertIn("!/clusters/homelab/openbao", source["spec"]["ignore"])
        self.assertNotIn("!/inventory", source["spec"]["ignore"])
        self.assertNotIn("ClusterRole", {d["kind"] for d in self.private})
        for d in self.private:
            if d["kind"] == "Role":
                for rule in d["rules"]:
                    self.assertNotIn("delete", rule["verbs"])
                    self.assertNotIn("list", rule["verbs"])
                    self.assertNotIn("*", rule["verbs"])

    def test_native_mount_schema_conversion_preserves_generated_defaults(self):
        talosctl = os.environ["TALOSCTL"]
        self.assertEqual(run([talosctl, "version", "--client", "--short"]).strip(),
                         "Client:\nTalos v1.14.1")
        template = Path("infrastructure/talos/openbao-local-kubelet.yaml.tftpl").read_text()
        patch = template.replace("${kubernetes_version}", "v1.37.0")
        # Native generator produces disposable fixture PKI only in auto-cleaned tmp.
        with tempfile.TemporaryDirectory(prefix="openbao-talos-fixture-") as directory:
            run([talosctl, "gen", "config", "offline-fixture", "https://192.0.2.70:6443",
                 "--output-dir", directory, "--with-docs=false", "--with-examples=false",
                 "--kubernetes-version", "1.37.0"])
            original = Path(directory) / "controlplane.yaml"
            baseline = list(yaml.safe_load_all(original.read_text()))
            kubelet = next(d for d in baseline if d.get("kind") == "KubeletConfig")
            patched = run([talosctl, "machineconfig", "patch", str(original), "--patch", patch])
            candidate = Path(directory) / "candidate.yaml"
            candidate.write_text(patched)
            run([talosctl, "validate", "--config", str(candidate), "--mode", "metal"])
            docs = list(yaml.safe_load_all(patched))
            self.assertNotIn("KubeletConfig", {d.get("kind") for d in docs})
            legacy = next(d["machine"]["kubelet"] for d in docs if "machine" in d)
            self.assertEqual(legacy["image"], kubelet["image"])
            self.assertEqual(legacy["defaultRuntimeSeccompProfileEnabled"],
                             kubelet["defaultRuntimeSeccompProfileEnabled"])
            self.assertIs(legacy["disableManifestsDirectory"], True)
            self.assertEqual(legacy["extraMounts"], [{
                "destination": "/var/mnt/openbao-poc", "source": "/var/mnt/openbao-poc",
                "type": "bind", "options": ["bind", "rshared", "rw"],
            }])
            restored = [d for d in docs if d.get("kind") != "KubeletConfig"]
            for d in restored:
                if "machine" in d:
                    del d["machine"]["kubelet"]
            # Never print even disposable fixture PKI on assertion failure.
            self.assertTrue([d for d in baseline if d.get("kind") != "KubeletConfig"] == restored,
                            "An unrelated Talos document/default was changed")

    def test_host_flag_default_off_selected_node_only(self):
        variables = Path("infrastructure/talos/variables.tf").read_text()
        main = Path("infrastructure/talos/main.tf").read_text()
        self.assertIn('variable "openbao_local_storage_node"', variables)
        self.assertIn('default     = ""', variables)
        self.assertIn('each.key == var.openbao_local_storage_node ?', main)
        self.assertNotIn("talos_machine_configuration_apply", main)
        self.assertIn("prevent_destroy = true", main)


if __name__ == "__main__":
    unittest.main()
