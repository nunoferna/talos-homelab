# Talos etcd backups (prepared, not active)

This directory adapts Sidero Labs' upstream `talos-backup` CronJob. It invokes
only `/talos-backup`: no personal backup scripts, fork or custom container.
It is intentionally **not referenced by `clusters/homelab`**, and the CronJob is
suspended. Preparing these files does not establish working backups.

The current milestone is a **one-shot PoC**, not a backup service. Use the
[inactive PoC overlay](../talos-poc) and [PoC runbook](../../../docs/recovery-poc.md).
Keep this CronJob suspended; recurring frequency, freshness alerts and destructive
restore testing are deferred. The production activation gates below describe
later use, not requirements to claim this limited PoC's acceptance result.

## Artifact and maturity

The public multi-architecture image index was inspected on 2026-10-03:

`ghcr.io/siderolabs/talos-backup@sha256:7fc186ff37a3137f470082cb609bf1dc3bcece13dd9a6421ec09cfdf4f33ae6c`

The index contains Linux amd64 and arm64 images. OCI metadata identifies the
upstream repository and an April 28, 2026 build date, but does not include a
source-revision label. Upstream HEAD at inspection was
`b9fd478c333045e173ad6d311102ee471e0b15b3`; this is contextual evidence, not a
verified image-to-commit attestation. Do not substitute the older beta tag:
its encryption environment-variable contract differs.

Upstream has prerelease tags only, and its current source uses the Talos 1.12.6
client. The environment runs Talos 1.14.1. Wire compatibility and successful
backup must be tested, not assumed from the source label or manifest rendering.
Use an isolated integration check and record the image's actual behavior before
production activation. An immutable digest is reproducible, not proof of safety.

## Ownership and private inputs

- OpenTofu renders Talos `KubeTalosAPIAccessConfig` when
  `enable_etcd_backup_api_access=true`; default is false. Delivery to nodes
  requires a reviewed code-driven operation, not an interactive patch.
- Flux will own this namespace, service accounts, CronJob and Cilium policy once
  all prerequisites are met. The private orchestration path should declare one
  Flux `Kustomization` using the public Git source and this directory's path,
  with private `spec.patches` for the exact R2 endpoint policy. It must depend on
  the private inputs' ready `Kustomization`. Do not also add this directory to the
  public root: two reconcilers must not own the same Kubernetes objects.
- Talos, not Git or OpenTofu, generates the `talos-backup-identity` Secret.
- The private repository must supply `ConfigMap/talos-backup-target` with
  `endpoint` (HTTPS R2 S3 endpoint), `bucket` (dedicated private backup bucket),
  and `age-recipients` (comma-separated public native age recipients).
- The private repository supplies `Secret/talos-backup-r2` containing only
  `access-key-id` and `secret-access-key`, using an explicitly allowlisted SOPS
  bootstrap exception. A private Flux source and SOPS decryption must be prepared
  before this path is enabled; neither is configured by this change.

Do not copy the existing state bucket credentials into the pod. Scope a separate
object credential to the backup bucket. R2's standard object read/write token
also grants deletion; do not describe it as upload-only. Use retention locks,
separate retention administration, and account recovery protections to compensate.
Backup authentication must not depend on ESO/OpenBao being available.

## Security and activation gates

1. Record independently accessible age recovery-key custody in two locations.
   Private identities, Talos bootstrap secrets and break-glass credentials stay
   outside Git and outside the privileged deployment runner.
   Follow the [key-custody ceremony](../../../docs/recovery-key-custody.md);
   backup recovery and Flux SOPS must use separate identities.
2. Prepare the R2 bucket, public-access restrictions, retention/lifecycle rules
   and scoped credentials through reviewed code. Never put a bucket-wide lock
   on the live OpenTofu backend or its lock files.
   The separate [R2 recovery root](../../../infrastructure/recovery/README.md)
   prepares the destination without managing the existing state bucket.
3. Measure account usage and ciphertext sizes. The proposed 15-minute interval
   is not an approved retention policy: it creates 96 snapshots/day. Thirty days
   at 10 MB each is 28.8 GB for etcd alone, beyond the R2 free allowance.
4. Validate the opt-in Talos patch, review its plan and deliver it through the
   controlled foundation workflow. Confirm Talos' ServiceAccount CRD and
   generated identity are available. Do not grant `os:admin` or `os:reader`.
5. Provide the private ConfigMap and SOPS Secret through the authenticated
   private Git source. Validate HTTPS, actual recipients and bucket ownership.
6. Replace the public Cilium FQDN wildcard with the exact private endpoint using
   the owning Flux `Kustomization`'s patches; include jurisdiction hostnames if used.
   Validate DNS and remote/local-node Talos API access, and audit additive rules.
7. Use a reviewed, separately declared one-shot Job from the same pod spec to
   test the published artifact, actual credentials and snapshot upload. Do not
   manually create a Job or edit the live CronJob. Record failures and keep the
   schedule suspended until downloaded snapshots decrypt and inspect correctly.
8. Enable the reviewed schedule and an out-of-cluster stale-backup alert only
   after transport, retention, age decryption and native inspection succeed.
   Record an isolated restore drill before declaring the platform recoverable.

The pod uses restricted PSA, no Kubernetes API token/RBAC, read-only root,
snapshot-only Talos identity and memory-backed scratch storage. Its memory and
scratch limits must be sized against the actual database plus simultaneous
plaintext/compressed/encrypted copies. Large snapshots can fail or OOM; errors
must alert rather than silently create a backup gap. Swap/hibernation policy on
the node also matters to the confidentiality of tmpfs contents.

## Download, decrypt and inspect

Use native tools on an approved recovery workstation, outside all Git worktrees.
Provision tools through reviewed code: age, zstd, an S3 client and `etcdutl`
matching the recorded etcd version (the Talos 1.14.1 release uses etcd 3.7.1).
Do not expose recovery private keys to CI.

Record the exact object key, size, ciphertext checksum, software versions and
retrieval time privately. Download that exact object using the scoped recovery
identity. Then use native commands, with paths in private encrypted scratch:

```sh
age --decrypt --identity /PRIVATE/backup-key.txt \
  --output /PRIVATE/scratch/snapshot.snap.zst /PRIVATE/download/snapshot.snap.zst.age
zstd --decompress --output /PRIVATE/scratch/snapshot.snap /PRIVATE/scratch/snapshot.snap.zst
etcdutl snapshot status /PRIVATE/scratch/snapshot.snap --write-out=json
```

The expected suffix is `.snap.zst.age` in the current upstream compressor;
local filenames above are arbitrary. Inspect the actual object's format before
decompressing. Successful authenticated decryption and database inspection are
necessary checks, **not** proof of a successful restore. Remove temporary
plaintext through the recovery workstation's controlled cleanup process; deletion
is not secure erasure on a plain filesystem.

## Restore drill and disaster procedure

Keep destructive restore testing outside the live three-node cluster. Prepare
isolated disposable Talos nodes with no network access to production, separate
addresses and no access to production backup writers or application credentials.
Restored Flux and other controllers must not reconcile production automatically.

Archive the Git commits, encrypted state, bootstrap identity, node configuration,
artifact pins and recovery runbook independently so GitHub/OpenBao availability
is not required to begin recovery. On a real incident, first determine whether
quorum can be recovered without restoration. Otherwise:

1. Obtain a known-good snapshot and independently held identity/configuration.
2. Follow the **matching Talos version's disaster-recovery procedure** to prepare
   replacement control-plane nodes using the retained cluster identity.
3. Recover etcd on one prepared node with the selected snapshot, then verify
   membership/quorum and API health before re-enabling controllers.
4. Verify Cilium and restore foundation ownership without blind re-creation or
   duplicate imports; re-enable Flux only against explicitly reviewed commits.
5. Later, restore OpenBao from its separate native Raft snapshot, unseal using
   the independently held Shamir shares, verify a test secret, then enable ESO.

etcd snapshots do not contain application PVC contents, OpenBao's Raft data or
OpenTofu state. OpenBao's official snapshot CronJob and Velero application/PV
backups are separate later layers. Do not use raw copies of live OpenBao files
as a substitute for an application-consistent Raft snapshot.

Rollback before activation is a Git revert: the Talos option defaults off and
the active Flux root remains untouched. After activation, suspend via Git and
preserve backup objects/evidence; never delete the last verified recovery point
or disable the snapshot role before the schedule has stopped.

## Validation and sources

```sh
kubectl kustomize platform/backup/talos
kubectl kustomize clusters/homelab
yamllint .
tofu fmt -check -diff -recursive infrastructure
tofu -chdir=infrastructure/talos validate
```

These are local/static checks; no live plan or deployment was performed by this
preparation. A real saved plan and its approval are required before any apply.

- [Upstream Talos backup](https://github.com/siderolabs/talos-backup)
- [Talos API-access document](https://docs.siderolabs.com/talos/v1.14/reference/configuration/kubernetes/kubetalosapiaccessconfig)
- [Talos recovery procedure](https://docs.siderolabs.com/talos/v1.14/build-and-extend-talos/cluster-operations-and-maintenance/disaster-recovery)
- [R2 pricing](https://developers.cloudflare.com/r2/pricing/)
- [R2 bucket locks](https://developers.cloudflare.com/r2/buckets/bucket-locks/)
- [OpenBao native automated snapshots](https://openbao.org/docs/concepts/storage/#automated-snapshot)
- [Velero backup model](https://velero.io/docs/v1.18/how-velero-works/)
