# Keycloak: selected, not deployed

Keycloak will provide human OIDC login to OpenBao and future applications.
ESO will use Kubernetes service-account authentication, not human OIDC.

Use the official namespace-scoped Keycloak Operator, pinned upstream manifests
reconciled by Flux. No OLM installation or experimental cluster-wide Helm chart
is needed. Start with one instance and MFA; this is a PoC, not HA identity.

Before deployment, confirm a stable HTTPS hostname reachable by the Mac and
OpenBao, and separate PostgreSQL persistence. The cluster currently has no
ingress controller or general-purpose storage provisioner. Do not reuse
OpenBao's database credentials, PV or data directory for Keycloak.

Keep necessary bootstrap inputs encrypted in private Git, independent of
OpenBao/ESO. Retain independent emergency access. Public Git owns non-secret
resources; operator records and site details stay private. No userpass fallback,
OIDC client secret, Keycloak server or new database is created in this stage.

References: [official operator installation](https://www.keycloak.org/operator/installation),
[database, hostname and TLS prerequisites](https://www.keycloak.org/operator/basic-deployment).
