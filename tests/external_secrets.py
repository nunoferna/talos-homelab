"""Offline checks for the empty ESO PoC; no credentials or cluster calls."""

import hashlib
import os
from pathlib import Path
import subprocess
import unittest

import yaml


CHART_SHA256 = "8199b42fe80b871c6a86233a80bb14f599fd6e1e6462c1216d836577f845e161"
NAMESPACE = "external-secrets"
FORBIDDEN = {
    "Secret", "SecretStore", "ClusterSecretStore", "ExternalSecret",
    "ClusterExternalSecret", "PushSecret", "ClusterPushSecret",
    "PersistentVolume", "PersistentVolumeClaim", "Ingress", "Job", "CronJob",
    "ValidatingWebhookConfiguration", "MutatingWebhookConfiguration",
    "ClusterRole", "ClusterRoleBinding",
}


def render(path):
    result = subprocess.run(
        ["kubectl", "kustomize", path], check=True, capture_output=True, text=True
    )
    return [doc for doc in yaml.safe_load_all(result.stdout) if doc]


class ExternalSecretsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.desired = render("platform/external-secrets/resources")
        cls.release = next(doc for doc in cls.desired if doc["kind"] == "HelmRelease")
        archive = Path(os.environ["ESO_CHART_ARCHIVE"])
        if hashlib.sha256(archive.read_bytes()).hexdigest() != CHART_SHA256:
            raise ValueError("ESO chart archive checksum does not match the reviewed release")
        helm_version = subprocess.run(
            ["helm", "version", "--template", "{{.Version}}"],
            check=True, capture_output=True, text=True,
        ).stdout
        if helm_version.split("+")[0] != "v4.3.0":
            raise ValueError("Use the reviewed Helm 4.3.0 offline renderer")
        result = subprocess.run(
            ["helm", "template", NAMESPACE, str(archive), "--namespace", NAMESPACE,
             "--kube-version", "1.37.0", "--skip-tests", "--values", "-"],
            input=yaml.safe_dump(cls.release["spec"]["values"]),
            check=True, capture_output=True, text=True,
        )
        cls.chart = [doc for doc in yaml.safe_load_all(result.stdout) if doc]

    def test_public_root_activates_only_the_eso_bridge(self):
        docs = render("clusters/homelab")
        bridge = next(doc for doc in docs if doc["metadata"]["name"] == NAMESPACE)
        self.assertEqual(bridge["kind"], "Kustomization")
        self.assertEqual(bridge["spec"]["sourceRef"], {
            "kind": "GitRepository", "name": "flux-system",
        })
        self.assertEqual(bridge["spec"]["path"], "./platform/external-secrets/resources")
        self.assertIs(bridge["spec"]["prune"], True)
        self.assertIs(bridge["spec"]["force"], False)
        self.assertEqual(bridge["spec"]["healthChecks"], [{
            "apiVersion": "helm.toolkit.fluxcd.io/v2", "kind": "HelmRelease",
            "name": NAMESPACE, "namespace": NAMESPACE,
        }])
        self.assertNotIn("backup-sync", {doc["metadata"]["name"] for doc in docs})
        self.assertNotIn("HelmRelease", {doc["kind"] for doc in docs})

    def test_official_exact_chart_and_no_private_inputs(self):
        source = next(doc for doc in self.desired if doc["kind"] == "HelmRepository")
        self.assertEqual(source["spec"], {
            "interval": "1h", "url": "https://charts.external-secrets.io",
        })
        self.assertEqual(self.release["spec"]["chart"]["spec"], {
            "chart": NAMESPACE, "version": "2.11.0",
            "sourceRef": {"kind": "HelmRepository", "name": NAMESPACE},
        })
        self.assertEqual(self.release["spec"]["releaseName"], NAMESPACE)
        self.assertNotIn("valuesFrom", self.release["spec"])
        for doc in self.desired + self.chart:
            self.assertNotIn(doc["kind"], FORBIDDEN)
            namespace = doc.get("metadata", {}).get("namespace")
            if namespace:
                self.assertEqual(namespace, NAMESPACE)

    def test_namespace_and_crds_survive_controller_rollback(self):
        namespace = next(doc for doc in self.desired if doc["kind"] == "Namespace")
        self.assertEqual(namespace["metadata"]["annotations"][
            "kustomize.toolkit.fluxcd.io/prune"], "disabled")
        self.assertEqual(namespace["metadata"]["labels"][
            "pod-security.kubernetes.io/enforce"], "restricted")
        crds = [doc for doc in self.chart if doc["kind"] == "CustomResourceDefinition"]
        names = {doc["metadata"]["name"] for doc in crds}
        self.assertIn("externalsecrets.external-secrets.io", names)
        self.assertIn("secretstores.external-secrets.io", names)
        for doc in crds:
            self.assertEqual(doc["spec"]["scope"], "Namespaced")
            self.assertEqual(doc["metadata"]["annotations"]["helm.sh/resource-policy"], "keep")
            self.assertNotEqual(doc["spec"].get("conversion", {}).get("strategy"), "Webhook")
        for name in names:
            self.assertFalse(name.startswith("cluster"))
            self.assertFalse(name.startswith("pushsecret"))

    def test_actual_rbac_has_no_cluster_secret_or_token_minting_access(self):
        roles = [doc for doc in self.chart if doc["kind"] == "Role"]
        self.assertTrue(roles)
        for role in roles:
            self.assertEqual(role["metadata"]["namespace"], NAMESPACE)
            self.assertNotIn("aggregationRule", role)
            for rule in role["rules"]:
                self.assertNotIn("*", rule["verbs"])
                self.assertNotIn("*", rule.get("resources", []))
                self.assertNotIn("serviceaccounts/token", rule.get("resources", []))
                self.assertFalse(any(resource.startswith("cluster")
                                     for resource in rule.get("resources", [])))
        bindings = [doc for doc in self.chart if doc["kind"] == "RoleBinding"]
        self.assertTrue(bindings)
        for binding in bindings:
            self.assertEqual(binding["metadata"]["namespace"], NAMESPACE)
            self.assertEqual(binding["roleRef"]["kind"], "Role")
            self.assertTrue(all(subject.get("namespace") == NAMESPACE
                                for subject in binding["subjects"]))

    def test_one_hardened_controller_with_health_probes(self):
        deployments = [doc for doc in self.chart if doc["kind"] == "Deployment"]
        self.assertEqual(len(deployments), 1)
        deployment = deployments[0]
        self.assertEqual(deployment["spec"]["replicas"], 1)
        pod = deployment["spec"]["template"]["spec"]
        self.assertFalse(pod.get("hostNetwork", False))
        self.assertFalse(pod.get("hostPID", False))
        self.assertFalse(pod.get("hostIPC", False))
        self.assertEqual(len(pod["containers"]), 1)
        container = pod["containers"][0]
        self.assertEqual(container["image"], "ghcr.io/external-secrets/external-secrets:v2.11.0")
        args = container["args"]
        self.assertIn("--namespace=external-secrets", args)
        for flag in ("cluster-store", "cluster-external-secret", "cluster-push-secret", "push-secret"):
            self.assertIn(f"--enable-{flag}-reconciler=false", args)
        self.assertNotIn("--unsafe-allow-generic-targets=true", args)
        security = container["securityContext"]
        self.assertIs(security["allowPrivilegeEscalation"], False)
        self.assertIs(security["readOnlyRootFilesystem"], True)
        self.assertIs(security["runAsNonRoot"], True)
        self.assertEqual(security["capabilities"]["drop"], ["ALL"])
        self.assertEqual(security["seccompProfile"]["type"], "RuntimeDefault")
        self.assertEqual(container["livenessProbe"]["httpGet"]["port"], "live")
        self.assertEqual(container["readinessProbe"]["httpGet"]["port"], "live")
        self.assertIn({"name": "live", "containerPort": 8082, "protocol": "TCP"}, container["ports"])
        self.assertEqual(container["resources"], self.release["spec"]["values"]["resources"])
        self.assertNotIn("Service", {doc["kind"] for doc in self.chart})

    def test_network_allows_only_dns_api_and_node_health(self):
        policy = next(doc for doc in self.desired if doc["kind"] == "CiliumNetworkPolicy")
        self.assertEqual(policy["metadata"]["namespace"], NAMESPACE)
        self.assertEqual(policy["spec"]["endpointSelector"], {})
        self.assertEqual(policy["spec"]["ingress"], [{
            "fromEntities": ["host", "remote-node"],
            "toPorts": [{"ports": [{"port": "8082", "protocol": "TCP"}]}],
        }])
        self.assertEqual(policy["spec"]["egress"], [{
            "toEndpoints": [{"matchLabels": {
                "k8s:io.kubernetes.pod.namespace": "kube-system", "k8s:k8s-app": "kube-dns",
            }}],
            "toPorts": [{"ports": [
                {"port": "53", "protocol": "UDP"}, {"port": "53", "protocol": "TCP"},
            ]}],
        }, {
            "toEntities": ["kube-apiserver"],
            "toPorts": [{"ports": [
                {"port": "443", "protocol": "TCP"}, {"port": "6443", "protocol": "TCP"},
            ]}],
        }])


if __name__ == "__main__":
    unittest.main()
