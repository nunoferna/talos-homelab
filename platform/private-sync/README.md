# Inactive private-repository bridge

Preparation only: this directory is deliberately absent from clusters/homelab.
Neither merging these manifests nor merging private-root files creates a source
or changes the cluster. A separate public activation PR follows operator input
delivery and read-only readiness checks.

The public root will own private-sync, which uses a required private runtime
ConfigMap to render the repository URL. The bridge owns the authenticated source,
private-root Kustomization and bounded proof-only RBAC. No credentials or private
environment URL are present here. Do not put secret values in substitutions.

OpenTofu still owns only Flux's existing Operator/Instance Helm releases, and
Cilium remains exclusively OpenTofu-owned. This bridge introduces no OpenTofu
resource or provider change. Bootstrap credentials are a one-time operator-only
reviewed-code exception, not OpenTofu inputs or state attributes.

Expected operator-owned inputs in flux-system:

- ConfigMap/private-gitops-settings: PRIVATE_GITOPS_URL, an SSH URL.
- Secret/flux-private-repo: identity and known_hosts; repository-only read access.
- Secret/sops-age: one .agekey entry for the existing SOPS identity, never the
  recovery-only etcd backup identity. No controller-global decryption key is set.

The private source artifact includes only clusters/homelab. Its initial root
contains a single ConfigMap/private-gitops-proof. The private reconciler may create
ConfigMaps in flux-system, but can only get/patch/update/delete that named proof.
It cannot write Secrets, Flux CRs, RBAC, namespaces or backup resources. The
create exception is required by Kubernetes RBAC semantics; it is not a general
application identity. Later backup permissions and artifact paths need review.

The bridge has prune=false so removing it does not cascade-delete a private
source/RBAC tree. The private workload root has prune=true for its bounded proof
object. Both use force=false. Do not let the private root manage its own source,
reconciliation spec or RBAC: that would undermine its impersonation boundary.

The settings ConfigMap is required; missing configuration fails reconciliation.
Removing its URL key produces an invalid GitRepository URL, not a fallback to a
public source. Do not mark the reference optional. The initial proof validates
Git retrieval/reconciliation, not in-cluster SOPS decryption: no encrypted Secret
is reachable yet. Backup Job/CronJob activation remains a separate gate.

Before activation, rollback is a Git revert only; no runtime action is needed.
After activation, disable through reviewed Git without deleting credential
Secrets, revoking the deploy key or deleting workloads until the live state and
ownership are inspected. Credential rotation is separate; no overwrite command
is included in preparation.

Removing the bridge alone does **not** stop its retained children. To stop private
reconciliation after activation, first review spec.suspend=true for both the
private GitRepository and private-root Kustomization in resources/, let the still
active bridge deliver it, and verify suspension before removing any bridge root.

Sources: [Flux SSH authentication](https://fluxcd.io/flux/components/source/gitrepositories/#ssh-authentication),
[Flux decryption](https://fluxcd.io/flux/components/kustomize/kustomizations/#decryption),
[Flux impersonation](https://fluxcd.io/flux/components/kustomize/kustomizations/#role-based-access-control).
