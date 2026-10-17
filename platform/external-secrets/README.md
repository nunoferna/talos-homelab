# External Secrets Operator

Flux owns the official ESO chart. This stage upgrades the empty controller
directly from 2.11.0 to 2.13.0 without expanding access, as requested for this
empty PoC. This skips upstream's recommended one-minor-at-a-time upgrade path.

## Current boundary

- One controller, scoped to `external-secrets`; no application namespaces.
- No stores, ExternalSecrets, provider credentials or token-minting permission.
- Cluster-wide features, webhook and certificate controller are disabled.
  Admission webhook validation is therefore absent.
- Cilium permits DNS/API egress and node health probes, not OpenBao access.
  This is not a host firewall.

Kubernetes 1.37 is outside ESO's published 1.36 test coverage, including the
current 2.13 release. On 2026-10-17 the operator accepted this compatibility
exception for disposable-data provider integration, not production use.
Recheck [support and upgrade guidance](https://external-secrets.io/latest/introduction/stability-support/)
before changing scope. This upgrade grants no provider access.

## Validation and rollback

Existing CI verifies the official chart archive's release SHA-256 and renders
its actual RBAC/security settings with Helm 4.3.0 and Kubernetes 1.37 capabilities.
The checksum is an offline check, not a Flux digest pin or compatibility proof.

After merge, use read-only checks: Flux/Helm Ready, one ready controller,
established CRDs, no stores/ExternalSecrets, and no new controller errors.
ESO must still lack Secret access in `flux-system` and TokenRequest access.
Fix failures through reviewed Git, not manual Helm or RBAC changes.

Review rollback against upstream notes; CRDs are retained and Helm rollback
does not downgrade their schemas. Never delete CRDs as routine rollback.

## Next: OpenBao connection

After the upgrade and reviewed integration changes, use Kubernetes authentication
with short-lived service-account tokens, verified TLS, a namespace `SecretStore`
and a read-only policy for that application's exact KV path. OpenBao uses its
own rotating pod token for TokenReview; no static reviewer JWT or root token
belongs in ESO. The [Vault provider](https://external-secrets.io/latest/provider/openbao/)
also supports OpenBao; it does not deploy HashiCorp Vault.

Add access only for the chosen application namespace. No wildcard policies,
cluster-wide store or demo workload. Configure audit logging and non-root
operator access before real application secrets. SOPS remains bootstrap-only;
HA, storage changes and recovery work remain deferred.
