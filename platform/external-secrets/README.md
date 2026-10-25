# External Secrets Operator

Flux owns the official ESO 2.13.0 chart. One controller runs in
`external-secrets` and watches only `kagent`, with namespace Roles rather than
cluster-wide Secret access. Cluster stores, push secrets, webhook and certificate
controller remain disabled. The Kubernetes 1.37 compatibility exception remains
accepted for this disposable-data PoC; upstream tests through 1.36.

`kagent/SecretStore/openbao` uses verified internal HTTPS and Kubernetes auth at
`kubernetes-apps`. ESO can mint a token only for `kagent/openbao-kagent`, with
audience `openbao`. OpenBao uses its rotating pod credential for TokenReview;
no static token, reviewer JWT or root credential is stored in ESO.

The OpenBao role grants read-only `kv/data/homelab/kagent/*` access with a
five-minute token and ten-minute maximum. Cilium permits the controller to reach
only DNS, the API and OpenBao. No ExternalSecret or kagent workload is created
until its real model credential is chosen and entered through OpenBao.

Verify the controller, `eso-kagent` and SecretStore are Ready. Confirm ESO cannot
read Secrets in `flux-system` or mint tokens for other service accounts. Existing
CI renders the checksum-pinned official chart and checks its security boundary.
Namespaces and CRDs are retained; never delete them as routine rollback.

References: [OpenBao provider](https://external-secrets.io/latest/provider/openbao/),
[Kubernetes authentication](https://external-secrets.io/latest/provider/hashicorp-vault/#kubernetes-authentication).
