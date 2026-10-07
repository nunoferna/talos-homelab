"""Offline Rook preparation checks; no disks, credentials or live API calls."""

import hashlib
import os
from pathlib import Path
import subprocess
import unittest

import yaml


CHART_SHA256 = "c070c7985deee72d7620e0377c07ce2afba28f566fbefe47bf934d00a5692cde"
NAMESPACE = "rook-ceph"


def render(path):
    result = subprocess.run(
        ["kubectl", "kustomize", path], check=True, capture_output=True, text=True,
    )
    return [doc for doc in yaml.safe_load_all(result.stdout) if doc]


class RookPreparationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.desired = render("platform/rook-ceph/operator")
        cls.release = next(doc for doc in cls.desired if doc["kind"] == "HelmRelease")
        archive = Path(os.environ["ROOK_CHART_ARCHIVE"])
        if hashlib.sha256(archive.read_bytes()).hexdigest() != CHART_SHA256:
            raise ValueError("Rook chart archive does not match the reviewed checksum")
        version = subprocess.run(
            ["helm", "version", "--template", "{{.Version}}"],
            check=True, capture_output=True, text=True,
        ).stdout
        if version.split("+")[0] != "v4.3.0":
            raise ValueError("Use the reviewed Helm 4.3.0 offline renderer")
        result = subprocess.run(
            ["helm", "template", NAMESPACE, str(archive), "--namespace", NAMESPACE,
             "--kube-version", "1.37.0", "--skip-tests", "--values", "-"],
            input=yaml.safe_dump(cls.release["spec"]["values"]),
            check=True, capture_output=True, text=True,
        )
        cls.chart = [doc for doc in yaml.safe_load_all(result.stdout) if doc]

    def test_disconnected_and_suspended(self):
        for doc in render("clusters/homelab"):
            self.assertFalse(doc["metadata"]["name"].startswith("rook"))
            self.assertNotEqual(doc["metadata"].get("namespace"), NAMESPACE)
            if doc["kind"] == "Kustomization":
                self.assertNotIn("rook-ceph", doc["spec"]["path"])
        self.assertIs(self.release["spec"]["suspend"], True)

    def test_official_exact_chart_no_private_inputs(self):
        source = next(doc for doc in self.desired if doc["kind"] == "HelmRepository")
        self.assertEqual(source["spec"], {
            "interval": "1h", "url": "https://charts.rook.io/release",
        })
        self.assertEqual(self.release["spec"]["chart"]["spec"], {
            "chart": "rook-ceph", "version": "1.21.0",
            "sourceRef": {"kind": "HelmRepository", "name": "rook-release"},
        })
        self.assertNotIn("valuesFrom", self.release["spec"])
        self.assertEqual({doc["kind"] for doc in self.desired}, {
            "Namespace", "HelmRelease", "HelmRepository", "CiliumNetworkPolicy",
        })

    def test_no_storage_or_ceph_resource_instances(self):
        forbidden = {
            "Secret", "StorageClass", "PersistentVolume", "PersistentVolumeClaim",
            "Pod", "Job", "CronJob", "StatefulSet", "DaemonSet", "CSIDriver",
            "Ingress", "Service", "ObjectBucketClaim",
        }
        for doc in self.desired + self.chart:
            self.assertNotIn(doc["kind"], forbidden)
            # CRDs describe Ceph types but must not instantiate a storage cluster.
            self.assertFalse(doc["apiVersion"].startswith(("ceph.rook.io/", "csi.ceph.io/")))

    def test_one_operator_with_only_emptydir_mounts(self):
        deployments = [doc for doc in self.chart if doc["kind"] == "Deployment"]
        self.assertEqual(len(deployments), 1)
        deployment = deployments[0]
        self.assertEqual(deployment["metadata"]["name"], "rook-ceph-operator")
        self.assertEqual(deployment["spec"]["replicas"], 1)
        pod = deployment["spec"]["template"]["spec"]
        self.assertFalse(pod.get("hostNetwork", False))
        self.assertFalse(pod.get("hostPID", False))
        self.assertFalse(pod.get("hostIPC", False))
        self.assertTrue(pod["volumes"])
        for volume in pod["volumes"]:
            self.assertEqual(set(volume), {"name", "emptyDir"})
        self.assertEqual(len(pod["containers"]), 1)
        operator = pod["containers"][0]
        self.assertEqual(operator["image"], "docker.io/rook/ceph:v1.21.0")
        self.assertEqual(operator["args"], ["ceph", "operator"])
        env = {item["name"]: item.get("value") for item in operator["env"]}
        self.assertEqual(env["ROOK_CURRENT_NAMESPACE_ONLY"], "true")
        self.assertEqual(env["ROOK_DISABLE_DEVICE_HOTPLUG"], "true")
        security = operator["securityContext"]
        self.assertIs(security["runAsNonRoot"], True)
        self.assertIs(security["allowPrivilegeEscalation"], False)
        self.assertFalse(security.get("privileged", False))
        self.assertEqual(security["capabilities"]["drop"], ["ALL"])
        self.assertEqual(security["seccompProfile"]["type"], "RuntimeDefault")
        self.assertEqual(operator["resources"], self.release["spec"]["values"]["resources"])

    def test_discovery_loop_devices_and_csi_remain_off(self):
        config = next(doc for doc in self.chart if doc["kind"] == "ConfigMap"
                      and doc["metadata"]["name"] == "rook-ceph-operator-config")
        for flag in ("ROOK_ENABLE_DISCOVERY_DAEMON", "ROOK_CEPH_ALLOW_LOOP_DEVICES",
                     "ROOK_CREATE_CSI_OPERATOR_RESOURCES"):
            self.assertEqual(config["data"][flag], "false")
        self.assertIs(self.release["spec"]["values"]["csi"]["installCsiOperator"], False)
        for doc in self.chart:
            if doc["kind"] == "CustomResourceDefinition":
                self.assertNotEqual(doc["spec"]["group"], "csi.ceph.io")

    def test_retention_and_operator_only_namespace_policy(self):
        namespace = next(doc for doc in self.desired if doc["kind"] == "Namespace")
        self.assertEqual(namespace["metadata"]["annotations"][
            "kustomize.toolkit.fluxcd.io/prune"], "disabled")
        self.assertEqual(namespace["metadata"]["labels"][
            "pod-security.kubernetes.io/enforce"], "restricted")
        crds = [doc for doc in self.chart if doc["kind"] == "CustomResourceDefinition"]
        self.assertIn("cephclusters.ceph.rook.io", {doc["metadata"]["name"] for doc in crds})
        for doc in crds:
            self.assertEqual(doc["metadata"]["annotations"]["helm.sh/resource-policy"], "keep")
        policy = next(doc for doc in self.desired if doc["kind"] == "CiliumNetworkPolicy")
        self.assertEqual(policy["spec"]["endpointSelector"], {
            "matchLabels": {"k8s:app": "rook-ceph-operator"},
        })
        self.assertEqual(policy["spec"]["ingress"], [])
        self.assertEqual(len(policy["spec"]["egress"]), 2)
        dns, api = policy["spec"]["egress"]
        self.assertEqual(dns["toEndpoints"], [{"matchLabels": {
            "k8s:io.kubernetes.pod.namespace": "kube-system", "k8s:k8s-app": "kube-dns",
        }}])
        self.assertEqual(api["toEntities"], ["kube-apiserver"])
        self.assertEqual(api["toPorts"], [{"ports": [
            {"port": "443", "protocol": "TCP"}, {"port": "6443", "protocol": "TCP"},
        ]}])


if __name__ == "__main__":
    unittest.main()
