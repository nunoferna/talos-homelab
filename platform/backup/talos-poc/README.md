# One-shot recovery PoC (inactive)

This overlay adds a stable `Job/talos-backup-poc-v1` to the prepared backup
resources. Both the Job and the inherited CronJob are suspended. It is not
referenced by the live public Flux root. Building it does not upload a snapshot.

Kustomize copies the CronJob's complete pod template, retaining the pinned native
`talos-backup` binary, encryption, restricted identity, network-policy labels,
memory-backed scratch and private input references. No backup script is added.
The Job requests one completion with no failure retries and a ten-minute deadline.
Kubernetes does not guarantee exactly-once execution even for this configuration;
inspect all objects and account usage after the run.

There is deliberately no `ttlSecondsAfterFinished`, generated name or automatic
rerun. Keep the completed Job as evidence while it remains Git-managed. Configure
the owning private Flux Kustomization with `force: false`; do not force-replace
an immutable Job template, delete the Job manually or rename it to retry.
A failed or interrupted attempt needs a fresh review, including any objects
already uploaded, before authorizing another attempt.

## Execution boundary

Follow [the PoC runbook](../../../docs/recovery-poc.md). After the reviewed
bucket, scoped credentials, Talos backup-only permission, private Flux source,
SOPS input and exact endpoint policy are ready, first reconcile this overlay
still suspended. A separate reviewed private patch may change only this Job's
`spec.suspend` to false. The CronJob must stay suspended.

Do not use `kubectl create job`, `kubectl apply` or an interactive patch to start
the PoC. Read-only observations and the usual Flux resync are sufficient once
the reviewed activation commit has reconciled.

The acceptance check is actual snapshot upload, fresh download, authenticated
age decryption, decompression and native `etcdutl snapshot status`. No recurring
schedule, freshness alert, restore test or recovery SLA is claimed. Record and
retain encrypted evidence independently before the seven-day object expiry.

Sources: [Kubernetes Job suspension and execution semantics](https://kubernetes.io/docs/concepts/workloads/controllers/job/),
[native upstream backup](https://github.com/siderolabs/talos-backup).
