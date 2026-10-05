"""Offline bridge checks; no bootstrap credentials or cluster mutations."""

import subprocess
import unittest

import yaml


def render(path):
    result = subprocess.run(
        ["kubectl", "kustomize", path], check=True, capture_output=True, text=True
    )
    return list(yaml.safe_load_all(result.stdout))


class PrivateSyncTests(unittest.TestCase):
    def test_preparation_is_not_in_live_root(self):
        names = {doc["metadata"]["name"] for doc in render("clusters/homelab")}
        self.assertTrue(names.isdisjoint({"private-sync", "homelab-private"}))

    def test_required_runtime_input_and_no_cascade(self):
        bridge, = render("platform/private-sync")
        self.assertEqual(bridge["spec"]["postBuild"]["substituteFrom"], [
            {"kind": "ConfigMap", "name": "private-gitops-settings", "optional": False}
        ])
        self.assertIs(bridge["spec"]["prune"], False)
        self.assertIs(bridge["spec"]["force"], False)

    def test_source_and_decryption_are_separate_bounded_references(self):
        docs = render("platform/private-sync/resources")
        source = next(doc for doc in docs if doc["kind"] == "GitRepository")
        sync = next(doc for doc in docs if doc["kind"] == "Kustomization")
        self.assertEqual(source["spec"]["url"], "${PRIVATE_GITOPS_URL}")
        self.assertEqual(source["spec"]["secretRef"]["name"], "flux-private-repo")
        self.assertEqual(source["spec"]["ref"], {"branch": "main"})
        self.assertNotIn("!/secrets", source["spec"]["ignore"])
        self.assertEqual(sync["spec"]["serviceAccountName"], "private-gitops-reconciler")
        self.assertEqual(sync["spec"]["decryption"], {
            "provider": "sops", "secretRef": {"name": "sops-age"}
        })
        self.assertIs(sync["spec"]["force"], False)
        for doc in docs:
            self.assertNotIn(doc["kind"], {"Secret", "Job", "CronJob", "ClusterRole"})
        role = next(doc for doc in docs if doc["kind"] == "Role")
        self.assertEqual(role["rules"], [
            {"apiGroups": [""], "resources": ["configmaps"], "verbs": ["create"]},
            {"apiGroups": [""], "resources": ["configmaps"],
             "resourceNames": ["private-gitops-proof"],
             "verbs": ["get", "patch", "update", "delete"]}
        ])


if __name__ == "__main__":
    unittest.main()
