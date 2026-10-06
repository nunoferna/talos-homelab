"""Offline backup scaffold checks. No credentials, Talos delivery or backup run."""

from pathlib import Path
import subprocess
import tempfile
import unittest

import yaml

from private_sync import render


class BackupSyncTests(unittest.TestCase):
    def test_source_filter_allows_only_backup_paths(self):
        source = next(doc for doc in render("platform/backup-sync/resources")
                      if doc["kind"] == "GitRepository")
        with tempfile.TemporaryDirectory(prefix="homelab-backup-ignore-test-") as directory:
            subprocess.run(["git", "init", "--quiet", directory], check=True)
            Path(directory, ".gitignore").write_text(source["spec"]["ignore"])
            for path, excluded in {
                "clusters/homelab/backup/workload/kustomization.yaml": False,
                "clusters/homelab/backup/inputs/target.yaml": False,
                "secrets/bootstrap/kustomization.yaml": False,
                "secrets/bootstrap/talos-backup-r2.sops.yaml": False,
                "secrets/bootstrap/other.sops.yaml": True,
                "secrets/bootstrap/talos-backup-r2.sops.yaml.extra": True,
                "secrets/apps/app.sops.yaml": True,
                "inventory/homelab.yaml": True,
                "recovery/r2.json": True,
                ".github/workflows/recovery-apply.yaml": True,
                "clusters/homelab/private-gitops-proof.yaml": True,
                "public/backup/talos/cronjob.yaml": True,
            }.items():
                result = subprocess.run([
                    "git", "-c", "core.excludesFile=/dev/null", "-C", directory,
                    "check-ignore", "--no-index", "--quiet", "--", path,
                ], check=False)
                self.assertEqual(result.returncode, 0 if excluded else 1, path)

    def test_preparation_is_disconnected(self):
        live = render("clusters/homelab")
        self.assertNotIn("backup-sync", {doc["metadata"]["name"] for doc in live})
        self.assertFalse(any(doc["kind"] in {"Job", "CronJob"} for doc in live))
        bridge, = render("platform/backup-sync")
        self.assertFalse(bridge["spec"]["prune"])
        self.assertFalse(bridge["spec"]["force"])
        self.assertFalse(bridge["spec"]["postBuild"]["substituteFrom"][0]["optional"])

    def test_composition_and_dependency_order(self):
        docs = render("platform/backup-sync/resources")
        namespace = next(doc for doc in docs if doc["kind"] == "Namespace")
        self.assertEqual(namespace, yaml.safe_load(Path("platform/backup/talos/namespace.yaml").read_text()))
        source = next(doc for doc in docs if doc["kind"] == "GitRepository")
        self.assertEqual(source["metadata"]["name"], "homelab-backup")
        self.assertEqual(source["spec"]["include"], [{
            "repository": {"name": "flux-system"},
            "fromPath": "platform/backup", "toPath": "public/backup",
        }])
        self.assertEqual(source["spec"]["url"], "${PRIVATE_GITOPS_URL}")
        self.assertIn("!/secrets/bootstrap/talos-backup-r2.sops.yaml", source["spec"]["ignore"])
        syncs = {doc["metadata"]["name"]: doc["spec"] for doc in docs
                 if doc["kind"] == "Kustomization"}
        self.assertEqual(set(syncs), {
            "talos-backup-settings", "talos-backup-inputs", "talos-backup-poc",
        })
        for spec in syncs.values():
            self.assertEqual(spec["sourceRef"]["name"], "homelab-backup")
            self.assertFalse(spec["prune"])
            self.assertFalse(spec["force"])
            self.assertFalse(spec["wait"])
            self.assertTrue(spec["serviceAccountName"].startswith("backup-"))
        self.assertEqual(syncs["talos-backup-inputs"]["decryption"], {
            "provider": "sops", "secretRef": {"name": "sops-age"},
        })
        self.assertEqual(syncs["talos-backup-poc"]["dependsOn"], [
            {"name": "talos-backup-settings"}, {"name": "talos-backup-inputs"},
        ])
        self.assertFalse(syncs["talos-backup-poc"]["postBuild"]["substituteFrom"][0]["optional"])

    def test_no_private_escalation_or_job_deletion_permission(self):
        docs = render("platform/backup-sync/resources")
        self.assertFalse(any(doc["kind"] in {"Secret", "Job", "CronJob", "ClusterRole"}
                             for doc in docs))
        roles = [doc for doc in docs if doc["kind"] == "Role"]
        self.assertEqual(len(roles), 3)
        for role in roles:
            for rule in role["rules"]:
                self.assertNotIn("*", rule["apiGroups"] + rule["resources"] + rule["verbs"])
                self.assertFalse(set(rule["verbs"]) & {"delete", "deletecollection", "impersonate", "bind", "escalate"})
                self.assertFalse(set(rule["apiGroups"]) & {
                    "kustomize.toolkit.fluxcd.io", "source.toolkit.fluxcd.io",
                    "rbac.authorization.k8s.io",
                })
                if rule["verbs"] != ["create"]:
                    self.assertIn("resourceNames", rule)
            if role["metadata"]["name"] != "backup-inputs-reconciler":
                self.assertFalse(any("secrets" in rule["resources"] for rule in role["rules"]))

    def test_talos_document_remains_backup_only_and_preview_is_read_only(self):
        patch = yaml.safe_load(Path("infrastructure/talos/etcd-backup-api-access.yaml").read_text())
        self.assertEqual(patch["allowedRoles"], ["os:etcd:backup"])
        self.assertEqual(patch["allowedKubernetesNamespaces"], ["platform-backup"])
        play, = yaml.safe_load(Path("management/ansible/talos-backup-access-preview.yaml").read_text())
        preview = next(task for task in play["tasks"] if task.get("no_log") is True)
        self.assertIn("--dry-run", preview["ansible.builtin.command"]["argv"])
        self.assertIn("--mode=no-reboot", preview["ansible.builtin.command"]["argv"])
        self.assertFalse(preview["changed_when"])


if __name__ == "__main__":
    unittest.main()
