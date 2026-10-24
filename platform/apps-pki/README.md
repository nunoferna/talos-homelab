# Application certificate authority

cert-manager and its narrow PKI access prerequisites are enabled. This stage
activates private site inputs and gateway certificate reconciliation after the
approved OpenBao bootstrap. Gateway exposure remains suspended; client trust
requires separate approval. Merge the paired private public-CA input first.

The root signing key stays outside the cluster. OpenBao generates and retains a
non-exported intermediate key; cert-manager submits gateway CSRs using short-lived,
audience-bound Kubernetes authentication. The namespaced Issuer is limited to
apps.internal server certificates. cert-manager owns
`apps-gateway/apps-internal-tls`, with 90-day certificates and renewal 30 days
before expiry. Git never owns that leaf key.

Before activating issuance, configure the OpenBao intermediate/auth/policy through
the private `gateway/operator/pki.yaml` workflow, supply the public OpenBao TLS CA
in private inputs, then activate the Issuer and verify Ready. This requires a
dedicated external root (`pathlen:1`) with verified off-cluster custody; preserve
the legacy leaf-only root (`pathlen:0`). First bootstrap is a separate approved
operator stage; later rotation needs separate review.

OpenBao's own bootstrap TLS remains independent: cold startup and unseal must
work while the application CA is unavailable. Existing valid gateway certificates
continue serving while OpenBao is sealed; issuance/renewal resumes after unseal.
Long shutdowns still require expiry checks.

The controller watches only `apps-gateway`; chart RBAC is narrowed by pinned
post-render patches. cainjector reads Secrets only in `cert-manager` and retains
cluster webhook configuration access for its own webhook CA. No ClusterIssuer,
ACME, ingress/gateway shim, CSR controller or application secret access is enabled.
Only Git reviewers/platform administrators may create certificate resources in
`apps-gateway`; the built-in approver is restricted to this Issuer.

cert-manager 1.21.3 tests Kubernetes through 1.36. The operator accepted 1.37 as a
disposable-data PoC exception on 2026-10-24; this is not upstream support.

References: [OpenBao PKI](https://openbao.org/docs/secrets/pki/considerations/),
[cert-manager Vault Issuer](https://cert-manager.io/docs/configuration/vault/).
