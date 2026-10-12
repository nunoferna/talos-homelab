"""Offline Longhorn preparation checks; no credentials or cluster API calls."""

import hashlib
import os
from pathlib import Path
import subprocess
import tarfile
import tempfile
import unittest

import yaml


CHART_SHA256 = "e57f010d2a8bcf0da5b8b03ffecf49c5bc35ddc2663588ce8f22b7567b6133ed"
NAMESPACE = "longhorn-system"


def render(path):
    result = subprocess.run(
        ["kubectl", "kustomize", path], check=True, capture_output=True, text=True,
    )
    return [doc for doc in yaml.safe_load_all(result.stdout) if doc]


def verify_known_values(overrides, defaults, path="values"):
    """Catch silently ignored Helm keys; null/default free-form maps are leaves."""
    if not isinstance(defaults, dict) or not defaults:
        return
    for key, value in overrides.items():
        if key not in defaults:
            raise ValueError(f"Unknown chart value: {path}.{key}")
        if isinstance(value, dict):
            verify_known_values(value, defaults[key], f"{path}.{key}")


class LonghornPreparationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.desired = render("platform/longhorn/resources")
        cls.release = next(doc for doc in cls.desired if doc["kind"] == "HelmRelease")
        archive = Path(os.environ["LONGHORN_CHART_ARCHIVE"])
        if hashlib.sha256(archive.read_bytes()).hexdigest() != CHART_SHA256:
            raise ValueError("Longhorn chart differs from the reviewed official digest")
        with tarfile.open(archive) as chart:
            cls.chart_metadata = yaml.safe_load(chart.extractfile("longhorn/Chart.yaml"))
            defaults = yaml.safe_load(chart.extractfile("longhorn/values.yaml"))
        verify_known_values(cls.release["spec"]["values"], defaults)
        helm_version = subprocess.run(
            ["helm", "version", "--template", "{{.Version}}"],
            check=True, capture_output=True, text=True,
        ).stdout
        if helm_version.split("+")[0] != "v4.3.0":
            raise ValueError("Use the reviewed Helm 4.3.0 offline renderer")
        result = subprocess.run(
            ["helm", "template", "longhorn", str(archive), "--namespace", NAMESPACE,
             "--kube-version", "1.37.0", "--skip-tests", "--values", "-"],
            input=yaml.safe_dump(cls.release["spec"]["values"]),
            check=True, capture_output=True, text=True,
        )
        cls.chart = [doc for doc in yaml.safe_load_all(result.stdout) if doc]
        # Exercise the real Kustomize post-render patch, not a hand-simulated patch.
        with tempfile.TemporaryDirectory(prefix="longhorn-render-") as directory:
            root = Path(directory)
            (root / "chart.yaml").write_text(result.stdout, encoding="utf-8")
            kustomization = {
                "apiVersion": "kustomize.config.k8s.io/v1beta1", "kind": "Kustomization",
                "resources": ["chart.yaml"],
                **cls.release["spec"]["postRenderers"][0]["kustomize"],
            }
            (root / "kustomization.yaml").write_text(
                yaml.safe_dump(kustomization), encoding="utf-8",
            )
            cls.processed_chart = render(str(root))
        config = next(doc for doc in cls.chart if doc["kind"] == "ConfigMap"
                      and doc["metadata"]["name"] == "longhorn-default-setting")
        cls.settings = yaml.safe_load(config["data"]["default-setting.yaml"])

    def test_two_inactive_gates_and_no_disk_instances(self):
        self.assertIs(self.release["spec"]["suspend"], True)
        root = render("clusters/homelab")
        self.assertNotIn(NAMESPACE, {doc["metadata"]["name"] for doc in root})
        for doc in root:
            self.assertNotIn("longhorn", doc.get("spec", {}).get("path", ""))
        forbidden = {"Secret", "PersistentVolume", "PersistentVolumeClaim", "CronJob",
                     "UserVolumeConfig", "RawVolumeConfig", "Ingress", "HTTPRoute"}
        for doc in self.desired + self.chart:
            self.assertNotIn(doc["kind"], forbidden)
            self.assertNotEqual(doc["apiVersion"], "longhorn.io/v1beta2")
        self.assertNotIn("valuesFrom", self.release["spec"])
        jobs = [doc for doc in self.chart if doc["kind"] == "Job"]
        self.assertEqual({doc["metadata"]["name"] for doc in jobs}, {
            "longhorn-post-upgrade", "longhorn-uninstall",
        })
        for job in jobs:
            self.assertIn(job["metadata"]["annotations"]["helm.sh/hook"], {
                "post-upgrade", "pre-delete",
            })

    def test_exact_official_chart_and_known_values(self):
        source = next(doc for doc in self.desired if doc["kind"] == "HelmRepository")
        self.assertEqual(source["spec"], {"interval": "1h", "url": "https://charts.longhorn.io"})
        self.assertEqual(self.release["spec"]["chart"]["spec"], {
            "chart": "longhorn", "version": "1.13.0",
            "sourceRef": {"kind": "HelmRepository", "name": "longhorn"},
        })
        self.assertEqual(self.chart_metadata["version"], "1.13.0")
        self.assertEqual(self.chart_metadata["appVersion"], "v1.13.0")
        self.assertEqual(self.chart_metadata["kubeVersion"], ">=1.34.0-0")
        with self.assertRaises(ValueError):
            verify_known_values({"typo": False}, {"valid": None})

    def test_actual_shared_disk_and_replication_settings(self):
        expected = {
            "v1-data-engine": True, "v2-data-engine": False,
            "default-data-path": "/var/lib/longhorn",
            "create-default-disk-labeled-nodes": True,
            "system-managed-components-node-selector": "homelab.storage/longhorn:true",
            "storage-reserved-percentage-for-default-disk": "30",
            "storage-over-provisioning-percentage": "100",
            "storage-minimal-available-percentage": "25",
            "replica-soft-anti-affinity": False,
            "replica-disk-soft-anti-affinity": False,
            "allow-volume-creation-with-degraded-availability": False,
            "concurrent-replica-rebuild-per-node-limit": "1",
            "snapshot-max-count": "8", "snapshot-count-warning-threshold": "6",
            "deleting-confirmation-flag": False, "upgrade-checker": False,
            "allow-collecting-longhorn-usage-metrics": False,
        }
        for key, value in expected.items():
            self.assertEqual(self.settings[key], value, key)
        replica_count = self.settings["default-replica-count"]
        if isinstance(replica_count, str) and replica_count.startswith("{"):
            replica_count = yaml.safe_load(replica_count)["v1"]
        self.assertEqual(str(replica_count), "3")
        backup = next(doc for doc in self.chart if doc["kind"] == "ConfigMap"
                      and doc["metadata"]["name"] == "longhorn-default-resource")
        backup_values = yaml.safe_load(backup["data"]["default-resource.yaml"])
        self.assertFalse(backup_values["backup-target"])
        self.assertFalse(backup_values["backup-target-credential-secret"])
        self.assertEqual(backup_values["backupstore-poll-interval"], 0)

    def test_retention_and_no_default_class_or_public_ui(self):
        namespace = next(doc for doc in self.desired if doc["kind"] == "Namespace")
        self.assertEqual(namespace["metadata"]["labels"][
            "pod-security.kubernetes.io/enforce"], "privileged")
        for doc in (namespace, self.release):
            self.assertEqual(doc["metadata"]["annotations"][
                "kustomize.toolkit.fluxcd.io/prune"], "disabled")
        storage_class = next(doc for doc in self.desired if doc["kind"] == "StorageClass")
        self.assertEqual(storage_class["metadata"]["name"], "longhorn-rwo")
        self.assertEqual(storage_class["metadata"]["annotations"][
            "storageclass.kubernetes.io/is-default-class"], "false")
        self.assertEqual(storage_class["reclaimPolicy"], "Retain")
        self.assertEqual(storage_class["volumeBindingMode"], "WaitForFirstConsumer")
        self.assertEqual(storage_class["parameters"]["numberOfReplicas"], "3")
        self.assertEqual(storage_class["parameters"]["dataEngine"], "v1")
        self.assertNotIn("longhorn-storageclass", {doc["metadata"]["name"] for doc in self.chart})
        crds = [doc for doc in self.processed_chart if doc["kind"] == "CustomResourceDefinition"]
        self.assertTrue(crds)
        for doc in crds:
            annotations = doc["metadata"]["annotations"]
            self.assertEqual(annotations["helm.sh/resource-policy"], "keep")
            self.assertIn("controller-gen.kubebuilder.io/version", annotations)
        for doc in self.chart:
            if doc["kind"] == "Service":
                self.assertEqual(doc["spec"].get("type", "ClusterIP"), "ClusterIP")

    def test_host_mount_is_opt_in_and_never_provisions_storage(self):
        patch_text = Path("infrastructure/talos/longhorn-legacy-kubelet.yaml.tftpl").read_text()
        patch = list(yaml.safe_load_all(patch_text.replace("${kubernetes_version}", "v1.37.0")))
        self.assertEqual(patch[0], {
            "apiVersion": "v1alpha1", "kind": "KubeletConfig", "$patch": "delete",
        })
        self.assertEqual(patch[1], {"machine": {"kubelet": {
            "image": "ghcr.io/siderolabs/kubelet:v1.37.0",
            "defaultRuntimeSeccompProfileEnabled": True,
            "disableManifestsDirectory": True, "extraMounts": [{
            "destination": "/var/lib/longhorn", "source": "/var/lib/longhorn",
            "type": "bind", "options": ["bind", "rshared", "rw"],
        }]}}})
        main = Path("infrastructure/talos/main.tf").read_text()
        self.assertIn('var.enable_longhorn_legacy_kubelet ? [templatefile(', main)
        variables = Path("infrastructure/talos/variables.tf").read_text()
        block = variables.split('variable "enable_longhorn_legacy_kubelet" {', 1)[1].split("}", 1)[0]
        self.assertIn("default     = false", block)
        schematic = yaml.safe_load(Path("platform/longhorn/host/image-factory-schematic.yaml").read_text())
        self.assertEqual(schematic["customization"]["systemExtensions"]["officialExtensions"], [
            "siderolabs/iscsi-tools", "siderolabs/util-linux-tools",
        ])

    def test_native_talos_schema_conversion_preserves_generated_defaults(self):
        talosctl = os.environ["TALOSCTL"]
        version = subprocess.run(
            [talosctl, "version", "--client", "--short"],
            check=True, capture_output=True, text=True,
        ).stdout
        self.assertEqual(version.strip(), "Client:\nTalos v1.14.1")
        patch_text = Path("infrastructure/talos/longhorn-legacy-kubelet.yaml.tftpl").read_text()
        patch_text = patch_text.replace("${kubernetes_version}", "v1.37.0")
        with tempfile.TemporaryDirectory(prefix="longhorn-talos-") as directory:
            root = Path(directory)
            for name, patch in (("baseline", None), ("longhorn", patch_text)):
                args = [talosctl, "gen", "config", "longhorn-fixture", "https://192.0.2.10:6443",
                        "--talos-version", "v1.14.1", "--kubernetes-version", "1.37.0",
                        "--with-docs=false", "--with-examples=false", "--output-types", "controlplane",
                        "--output", str(root / f"{name}.yaml")]
                if patch:
                    args.extend(["--config-patch", patch])
                subprocess.run(args, check=True, capture_output=True, text=True)
            subprocess.run(
                [talosctl, "validate", "--config", str(root / "longhorn.yaml"), "--mode", "metal"],
                check=True, capture_output=True, text=True,
            )
            baseline = list(yaml.safe_load_all((root / "baseline.yaml").read_text()))
            converted = list(yaml.safe_load_all((root / "longhorn.yaml").read_text()))
            kubelet = next(doc for doc in baseline if doc.get("kind") == "KubeletConfig")
            legacy = next(doc for doc in converted if "machine" in doc)["machine"]["kubelet"]
            self.assertEqual(legacy["image"], kubelet["image"])
            self.assertEqual(legacy["defaultRuntimeSeccompProfileEnabled"],
                             kubelet["defaultRuntimeSeccompProfileEnabled"])
            self.assertIs(legacy["disableManifestsDirectory"], True)
            self.assertFalse(any(doc.get("kind") == "KubeletConfig" for doc in converted))
            baseline_kinds = {doc["kind"] for doc in baseline if "kind" in doc}
            converted_kinds = {doc["kind"] for doc in converted if "kind" in doc}
            self.assertEqual(converted_kinds, baseline_kinds - {"KubeletConfig"})

    def test_user_deployed_and_system_components_require_approved_node_label(self):
        for doc in self.chart:
            if doc["kind"] in {"Deployment", "DaemonSet"}:
                pod = doc["spec"]["template"]["spec"]
                self.assertEqual(pod["nodeSelector"]["homelab.storage/longhorn"], "true")
        self.assertEqual(self.settings["system-managed-components-node-selector"],
                         "homelab.storage/longhorn:true")

    def test_candidate_policy_has_no_world_or_application_namespace_trust(self):
        policy = next(doc for doc in self.desired if doc["kind"] == "CiliumNetworkPolicy")
        self.assertEqual(policy["spec"]["endpointSelector"], {})
        for direction, endpoint_key, entity_key in (
            ("ingress", "fromEndpoints", "fromEntities"),
            ("egress", "toEndpoints", "toEntities"),
        ):
            for rule in policy["spec"][direction]:
                self.assertFalse({"world", "all", "cluster"} & set(rule.get(entity_key, [])))
                self.assertNotIn("toCIDR", rule)
                self.assertNotIn("toFQDNs", rule)
                for endpoint in rule.get(endpoint_key, []):
                    namespace = endpoint["matchLabels"]["k8s:io.kubernetes.pod.namespace"]
                    self.assertIn(namespace, {NAMESPACE, "kube-system"})
                    if namespace == "kube-system":
                        self.assertEqual(endpoint["matchLabels"]["k8s:k8s-app"], "kube-dns")


if __name__ == "__main__":
    unittest.main()
