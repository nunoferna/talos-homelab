# Suspended backup wiring — preparation only

This directory is **not** referenced by clusters/homelab. Merging preparation
does not deliver Talos configuration, create a namespace/Secret/Job, or upload a
snapshot. Do not add it to the root until the staged gates below pass.

OpenTofu 1.12.6 / Talos provider 0.12.0 retains the existing Talos identity and
renders the opt-in document. Helm provider 3.3.0 still owns Cilium and Flux
installation. Existing encrypted, locked R2 state and private reviewed-plan Pi
execution for Cilium/Flux are unchanged; Talos still uses its separate reviewed
local plan path. No provider upgrade or state migration is included.
The Talos rendering flag is not node delivery.

## Composition and resource ownership

The public-owned backup-sync scaffold creates the namespace, impersonation RBAC,
a separate authenticated homelab-backup source and three Flux Kustomizations.
The original homelab-private proof source/root/role are unchanged.

| Owner | Desired resources | Source |
| --- | --- | --- |
| backup-sync | Namespace, reconciliation SAs/roles/bindings, source, child Flux specs | Public |
| talos-backup-settings | Named endpoint settings ConfigMap in flux-system | Private |
| talos-backup-inputs | Named target ConfigMap and SOPS writer Secret in platform-backup | Private |
| talos-backup-poc | Native backup SAs, exact Cilium policy, suspended stable Job and CronJob | Private overlay + public base |

Flux GitRepository include composes only platform/backup from the existing public
source at public/backup in the new private artifact. No remote Kustomize loading,
custom runtime copier or backup script is needed. A reviewed public-base update
can trigger a new composed artifact even without a private commit; inspect both
source revisions/observedInclude when accepting reconciliation. Private CI pins
its offline public fixture; update that pin deliberately when changing the base.

The private artifact allowlists clusters/homelab/backup and two bootstrap files:
the existing writer ciphertext and its Kustomize wrapper. Inventory, workflows,
recovery settings, other secrets and control documents remain excluded. Artifact
filtering is not an authorization boundary: the deploy key reads the private
repository, and a Git writer can edit allowed workload paths.

The private root cannot modify Flux sources/Kustomizations, RBAC, namespaces or
cluster-wide objects. Separate reconciliation identities limit settings, writer
inputs and workload permissions. Create cannot be resourceNames-scoped in RBAC;
subsequent get/patch/update is named. No list/watch/delete/deletecollection,
impersonate/bind/escalate permission is granted. This does not sandbox an
authorized backup workload from its own snapshot/credential: review private Git
changes accordingly. Application workloads must not use this namespace.

All child Kustomizations use force=false, prune=false and wait=false. The workload
depends on the two input reconciliations. A suspended Job cannot Complete;
Ready here only means manifests applied, not a backup completed or a token works.
The native Talos-generated identity Secret is owned by Talos, not Flux/SOPS.
Only the SOPS identity, not the offline backup recovery identity, is in Flux.

## Staged gates

1. Merge public/private preparation; both reconciliation roots remain unchanged.
2. Review the existing Talos encrypted saved-plan path using the private opt-in
   tfvars. No PKI/bootstrap recreation, provider/backend change or other config
   change is acceptable. Apply only that separately approved exact plan.
3. Use the reviewed read-only preview playbook. Deliver the reviewed native
   document through a separately approved code path, one node at a time, with
   no reboot/reinstall/reset and readiness/quorum/security checks after each.
   **This preparation intentionally contains no delivery command.** Verify the
   serviceaccounts.talos.dev CRD and narrow live permissions before wiring Flux.
4. Recheck PoC credential expiry/scope, private bucket/domain audit, account usage
   and etcd size. Prepare the native recovery inspection tools before a run.
5. A separate public activation PR adds backup-sync to clusters/homelab. Verify
   both source revisions, three child Ready conditions, only the expected Secret
   name/type, exact policy endpoint and both suspension flags. Do not inspect
   or print the decrypted Secret. Confirm the Job has no Pods.
6. A separate private reviewed commit changes only the Job suspend patch to
   false. Never unsuspend the CronJob, rename/delete the Job, enable force or TTL.
   Verify the real downloaded/decrypted/decompressed snapshot with etcdutl;
   native SOPS reconciliation alone is not recovery proof.

The matching preview playbook uses explicit private path variables, checks the
workstation Kubernetes API/namespace UID and runs only native --dry-run
--mode=no-reboot patch previews. Sensitive previews are suppressed, not retained
or logged in CI. Exit status does not establish full configuration equivalence,
etcd quorum health or successful delivery. See the private runbook for commands.

## Rollback

Preparation rollback is a Git revert; neither live root reaches it. Once wired,
removing backup-sync alone does not stop retained child reconciliation. Stop
through reviewed suspend=true child/source changes while the bridge is active
and verify delivery read-only first. Suspending a running Job can terminate its
Pods and interrupt upload; preserve objects/evidence. Do not delete/recreate the
stable Job, identity, credentials, bucket or lock as an automated rollback.
Keep encrypted state and independently held keys; never replace current state
with an older snapshot. Disabling Talos access is a separate reviewed node change
after the run has stopped, not a bootstrap/identity reset.

Checks cover YAML and Ansible syntax, public-manifest safeguards, scoped RBAC and
dependency tests, private native Kustomize composition with ciphertext-only
assertions, scanning and existing CI. No actual plan/apply/decryption/upload in tests.

Sources: [Flux artifact inclusion](https://fluxcd.io/flux/components/source/gitrepositories/#include),
[Flux impersonation and dependencies](https://fluxcd.io/flux/components/kustomize/kustomizations/#role-based-access-control),
[upstream backup tool](https://github.com/siderolabs/talos-backup).
