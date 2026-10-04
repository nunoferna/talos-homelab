# One-shot etcd recovery PoC

The current goal is one requested backup run, not a recurring backup service.
Success means the upstream tool uploads an age-encrypted etcd snapshot and an
operator freshly downloads, decrypts and inspects it. This is not proof of a
successful restore or a continuously recoverable platform. No hourly schedule,
external freshness alert or destructive restore drill is required for this PoC.

Key custody has its own ceremony. Do not regenerate completed recovery keys.
Private key material and passphrases must remain outside Git, CI and the Pi.

## Code and ownership

- `infrastructure/recovery`: a separate OpenTofu 1.12.6 / Cloudflare 5.24.0 root
  for a new private Standard R2 bucket and seven-day prefix lock/expiry. It uses
  encrypted state and saved plans under `homelab/recovery.tfstate`, never changes
  the state bucket, and defaults to `backup_mode=poc`, `snapshots_per_day=0` and
  a 100,000,000-byte planning budget. There is no apply operation yet.
- `platform/backup/talos-poc`: an inactive Kustomize overlay with the stable
  `Job/talos-backup-poc-v1`, the shared native backup pod template and suspended
  CronJob. Neither path is added to `clusters/homelab` by preparation.
- Private control repository: reviewed identifiers/sizing, plan orchestration,
  exact endpoint policy, public recipients and the allowlisted SOPS writer input.
  The authenticated private Flux source and SOPS runtime identity are not yet
  bootstrapped. They must be delivered through reviewed code before reconciliation.

## Preparation gates

1. Record account-wide R2 usage and a conservative native etcd-size-based snapshot
   bound privately. Compression is not assumed. PoC projection is two objects
   times that bound times 1.25. The second object allows a possible duplicate:
   Kubernetes Jobs are not exactly-once, and this estimate is not an upload-count
   or billing cap. Include retained objects from earlier attempts in other usage.
   The budget plus other account usage must stay under the existing 8 GB planning
   ceiling. Snapshot bounds remain mandatory even though the cadence is zero.
2. Prepare protected `recovery-plan` runtime configuration and dedicated read
   token using the private runbook. Never send credentials through chat. Merge
   both public source and private control changes, then dispatch a plan against
   the full reviewed public SHA. Review the exact encrypted saved plan: one new
   bucket plus its three settings, no existing foundation/state resources.
3. Add a separately reviewed saved-plan apply path and write-credential boundary
   before creating the destination. Then provision a bucket-scoped object writer
   and a separate read-only recovery credential. Audit public-domain bindings;
   disabled `r2.dev` alone is not enough. Do not use state credentials in a pod.
4. Deliver the opt-in backup-only Talos API permission, private Flux source,
   SOPS runtime identity, private ConfigMap and encrypted writer Secret through
   reviewed foundation/bootstrap code. Never grant a broad Talos administrator
   identity to the Job. Do not make backups depend on OpenBao or ESO.
5. Declare one private Flux Kustomization sourcing `platform/backup/talos-poc`
   from public Git. It must depend on private inputs, patch Cilium's R2 wildcard
   to the exact private endpoint, use `force: false`, and not duplicate another
   reconciler's ownership. Initially leave Job and CronJob suspended. Do not
   wait for a suspended Job to complete as a Flux readiness gate.

## Authorize and observe one run

Use a separate reviewed private activation commit to set only the PoC Job's
`spec.suspend=false`. Keep the CronJob suspended. Do not use interactive resource
creation, patches, generated names or TTL cleanup. Keep the completed Job while
it remains desired in Git: deleting it permits reconciliation to create it again.
The PoC requests one completion, no failure retries and a ten-minute deadline,
but duplicates are still possible. Never promise exactly one object.

After reconciliation, the following commands are read-only. Use your existing
protected kubeconfig; do not copy it to CI or commit it:

```sh
kubectl --kubeconfig /PROTECTED/kubeconfig -n platform-backup get cronjob talos-backup
kubectl --kubeconfig /PROTECTED/kubeconfig -n platform-backup get job talos-backup-poc-v1
kubectl --kubeconfig /PROTECTED/kubeconfig -n platform-backup wait \
  --for=condition=complete job/talos-backup-poc-v1 --timeout=30s
kubectl --kubeconfig /PROTECTED/kubeconfig -n platform-backup get pods \
  -l batch.kubernetes.io/job-name=talos-backup-poc-v1
```

A timeout is not permission to recreate the Job. Inspect failure status read-only,
review any uploaded objects and correct code before authorizing another attempt.
Never paste unreviewed logs into chat: upstream errors may include private details.

## Operator-only verification

Use the protected recovery workstation, native age/zstd/etcdutl tools and the
separate read-only object credential. Obtain the actual endpoint, bucket and
object key privately. Inventory all objects from the attempt, then record the
selected object's size, ciphertext SHA-256, object key, retrieval time, artifact
versions and reviewed Git SHAs in private evidence.

Follow [download, decrypt and inspect](../platform/backup/talos/README.md#download-decrypt-and-inspect).
Only the operator unlocks the encrypted recovery kit and handles private keys
or decrypted snapshot contents. A successful fixture-key test is not a snapshot
test. Require authenticated snapshot decryption, successful decompression and
`etcdutl snapshot status` on the actual downloaded database. Do not restore it
into the live cluster. Provision the matching tools through reviewed code first.

Before seven-day expiry, retain the verified ciphertext and non-secret evidence
outside the expiring prefix, for example in the independently controlled private
OneDrive recovery location. Remove temporary plaintext through the existing
approved workstation cleanup process; deletion is not secure erasure on APFS.

## Rollback and later production use

Before activation, revert preparation through Git; no cloud/cluster change is
made by this PR. During an active run, a reviewed `suspend=true` patch terminates
unfinished Pods and may interrupt an upload. It does not undo uploaded objects.
Preserve those objects and evidence, and do not remove locks or destroy a bucket.
Keep the stable completed Job; remove it from desired Git before any separately
reviewed cleanup so Flux cannot recreate it. Secret access should be revoked only
after the run has stopped and retrieval/evidence are independently secured.

Production backups are a separate decision: select a recovery objective, measured
cadence/retention and budget; choose `backup_mode=scheduled` with matching nonzero
frequency; prepare alerts and isolated restore testing. Never unsuspend the
CronJob as part of this PoC.

Sources: [Kubernetes Job guarantees and suspension](https://kubernetes.io/docs/concepts/workloads/controllers/job/),
[upstream Talos backup](https://github.com/siderolabs/talos-backup),
[R2 Standard free-tier pricing](https://developers.cloudflare.com/r2/pricing/).
