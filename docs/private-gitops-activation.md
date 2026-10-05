# Activate private Git reconciliation, not backups

## Reviewed preconditions

On 2026-10-06 the operator reported successful execution of the merged guarded
bootstrap-input playbook. Read-only metadata checks observed Opaque Secrets
flux-private-repo and sops-age, plus ConfigMap/private-gitops-settings, all in
flux-system. Their creation time was 2026-10-05T23:24:17Z. The assistant did not
inspect Secret payloads, private identities, passphrases or configuration values.
The public source/root remained Ready before this change. The current private
root was inspected from Git and contains only ConfigMap/private-gitops-proof.

The playbook's reported success attests its cluster/recipient/read-only-key
guards, not independent verification of Secret contents or actual SSH access.
The latter is established only by subsequent source/root Ready observations.
Input presence is not proof of in-cluster SOPS decryption.

## What merging this activation changes

clusters/homelab gains one resource directory: platform/private-sync. Existing
Flux will create Kustomization/private-sync, whose required runtime settings
render the private repository source and proof-only reconciliation/RBAC. The
public repository continues owning that wiring. The private workload root uses
the private-gitops-reconciler ServiceAccount and cannot manage its own source,
Kustomization or RBAC.

No direct kubectl apply, flux bootstrap, controller reinstall, Helm release
change, OpenTofu plan/apply or state mutation is involved. The operator-delivered
bootstrap inputs remain outside both Flux inventories and OpenTofu state.
No new permission to read/write Kubernetes Secrets is granted to the private
workload identity; its ConfigMap create permission is namespace-wide because
Kubernetes cannot restrict create by resource name, with subsequent access
restricted to the named proof object.

The private source artifact includes only clusters/homelab. The committed
encrypted writer remains outside that artifact/root, and no platform-backup
resource, Job or CronJob is introduced. Talos API opt-in, backup-specific RBAC,
EU endpoint/egress wiring and a suspended one-shot overlay are separate changes.
The existing SOPS Secret is referenced, but no encrypted resource is reconciled
in this phase; do not describe the proof ConfigMap as a SOPS decryption test.

## Acceptance after merge: read-only checks

The assistant checks source/root conditions and revision metadata, verifies the
named proof ConfigMap is present and compares its non-secret data with Git.
These commands neither resync nor mutate anything. Use the existing protected
workstation kubeconfig/context; operators need not re-enter credentials:

```bash
kubectl --kubeconfig "${homelab_kubeconfig:?Set the protected kubeconfig path}" \
  --context "${homelab_context:?Set the verified homelab context}" \
  --namespace flux-system get gitrepositories,kustomizations
kubectl --kubeconfig "${homelab_kubeconfig:?Set the protected kubeconfig path}" \
  --context "${homelab_context:?Set the verified homelab context}" \
  --namespace flux-system get configmap private-gitops-proof
```

Expected: public source/root Ready at the activation commit, bridge Ready,
private source/root Ready at the reviewed private main revision, and exactly the
expected proof ConfigMap. Record both repository revisions and the observation
date in private evidence. Do not declare acceptance while any condition is
unknown/False or a revision is stale. Transient RBAC/source ordering failures
should retry naturally; inspect conditions/events without making live patches.
If reconciliation fails, make a reviewed fix rather than recreating keys or
reinstalling Flux. Do not inspect Secret values or publish private artifacts.

## Operator scratch cleanup

The bootstrap-input runbook permits operator cleanup after the three input
names/types have been verified. The assistant performs no key deletion. Keep
the verified encrypted local/OneDrive bundles and independently held unlocks.
Remove only the disposable local deploy identity and extracted SOPS identity
using the exact private runbook commands; no recursive deletion, bundle removal
or deploy-key revocation is required. Deletion is not secure erasure.

## Stop/rollback

Before merge, discard/revert this activation proposal; there is no runtime change.
After merge, a simple root-reference revert is **not** enough to stop private
reconciliation: the bridge uses prune=false and retains its source/root children.
First review spec.suspend=true on both private-source and private-root manifests
in platform/private-sync/resources, keeping the bridge active long enough to
deliver them. Verify suspension read-only before removing the bridge reference.
Preserve bootstrap Secrets, registered deploy key, age bundles and workloads.
No destructive rollback or state restore is included.

Sources: [Flux impersonation](https://fluxcd.io/flux/components/kustomize/kustomizations/#role-based-access-control),
[Flux decryption](https://fluxcd.io/flux/components/kustomize/kustomizations/#decryption),
[Flux artifact exclusions](https://fluxcd.io/flux/components/source/gitrepositories/#ignore-spec).
