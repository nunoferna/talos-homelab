"""Offline manifest checks only; this is not a backup implementation."""

import subprocess
import unittest

import yaml


def render(path):
    result = subprocess.run(
        ["kubectl", "kustomize", path], check=True, capture_output=True, text=True
    )
    return list(yaml.safe_load_all(result.stdout))


class RecoveryPocTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.documents = render("platform/backup/talos-poc")
        cls.job = next(doc for doc in cls.documents if doc["kind"] == "Job")
        cls.cron = next(doc for doc in cls.documents if doc["kind"] == "CronJob")

    def test_preparation_cannot_start_a_backup(self):
        self.assertIs(self.job["spec"]["suspend"], True)
        self.assertIs(self.cron["spec"]["suspend"], True)
        self.assertEqual(sum(doc["kind"] == "Job" for doc in self.documents), 1)
        for doc in render("clusters/homelab"):
            self.assertNotEqual(doc.get("metadata", {}).get("namespace"), "platform-backup")
            self.assertNotIn(
                doc.get("metadata", {}).get("name"),
                ("platform-backup", "talos-backup", "talos-backup-poc-v1"),
            )

    def test_pod_template_is_shared_without_drift(self):
        self.assertEqual(
            self.job["spec"]["template"],
            self.cron["spec"]["jobTemplate"]["spec"]["template"],
        )
        pod = self.job["spec"]["template"]["spec"]
        self.assertIs(pod["automountServiceAccountToken"], False)
        self.assertEqual(pod["restartPolicy"], "Never")
        self.assertEqual(pod["containers"][0]["command"], ["/talos-backup"])
        encryption = next(
            env for env in pod["containers"][0]["env"]
            if env["name"] == "DISABLE_ENCRYPTION"
        )
        self.assertEqual(encryption["value"], "false")

    def test_no_ttl_or_name_churn_or_failure_retries(self):
        self.assertEqual(self.job["metadata"]["name"], "talos-backup-poc-v1")
        self.assertNotIn("generateName", self.job["metadata"])
        self.assertNotIn("ttlSecondsAfterFinished", self.job["spec"])
        self.assertEqual(self.job["spec"]["backoffLimit"], 0)
        self.assertEqual(self.job["spec"]["completions"], 1)
        self.assertEqual(self.job["spec"]["parallelism"], 1)
        self.assertEqual(self.job["spec"]["activeDeadlineSeconds"], 600)


if __name__ == "__main__":
    unittest.main()
