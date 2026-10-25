# OpenBao: PostgreSQL-backed PoC

Flux deploys official Helm charts: OpenBao 0.30.3 (app 2.7.1), CloudNativePG
0.29.1 (operator 1.30.1) and PostgreSQL cluster 0.9.0 (PostgreSQL 17.11,
digest-pinned). Helm dependencies order operator → database → OpenBao.

## Architecture

- One normal OpenBao server; PostgreSQL backend, not dev mode or Raft.
- One PostgreSQL instance on cp01, using `/var/mnt/openbao-poc` on the existing
  filesystem. A retained, non-default static PV binds only `openbao-db-1`.
  OpenBao itself has no data PVC. No disk provisioning or Longhorn/Ceph.
- CNPG generates database credentials and TLS. OpenBao uses native Secret
  references and `verify-full`; only `ca.crt`, never the CA key, is mounted.
- Serving TLS is the exceptional SOPS input from private Git. Bootstrap/unseal
  custody and operator commands stay outside public Git and Kubernetes.
- Cilium isolates the server, database and operator. The LAN API hostname is
  `openbao.apps.internal`; the shared gateway verifies backend TLS against the
  public bootstrap CA and service DNS name. The UI is enabled in the staged
  configuration and becomes active after the approved restart and unseal.

## Operations

Merge reviewed Git changes; Flux reconciles the resources. Host delivery and
OpenBao initialization/unseal use reviewed local Ansible from the private repo.
Never initialize again after successful initialization. Pod replacement requires
manual unseal. Helm/Flux Ready alone does not prove OpenBao is unsealed.

Auditing is declared in the server configuration, with JSON/HMAC-protected
events to container stdout and unsafe API audit creation disabled. `OnDelete`
prevents an automatic restart: after Flux applies the configuration, use the
reviewed private restart procedure, then separately approve unseal. Until then,
the running process still uses its previous configuration. Treat logs as
sensitive; stdout is not durable or tamper-resistant audit storage. If the
only audit destination cannot write, OpenBao can block requests.

For read-only acceptance, check the child Flux reconciliation, three releases,
CNPG Ready, retained PVC/PV binding, verified TLS and native `bao status`.
OIDC access adds gateway ingress on 8200 and gateway egress on 443, plus the
Keycloak backend identity on 8080 for Cilium's pod-origin Gateway policy checks;
the provider's public CA is configured on the OIDC auth mount, without restarting
OpenBao. Flux owns the Keycloak client; the initial OpenBao auth configuration
uses reviewed private operator code. OpenBao's generated client secret stays
in the two services and protected operator memory, outside Git and Kubernetes
Secrets. The separate realm-automation seed is the documented SOPS exception.
The human role allows both the CLI callback and the exact HTTPS UI callback.
[Bounded ESO integration](../external-secrets/README.md) uses separate Kubernetes
authentication and a read-only policy for the `kagent` namespace.

## Limits

Disposable data only: no HA, failover or database backup. The 4 GiB PV is not
a quota and shares the OS/etcd disk. Node outage causes downtime; disk loss
loses data. Retention is not recovery. Never delete the namespace, CNPG Cluster,
PV/PVC or host directory, or remove the serving mount, as routine rollback.
Suspend through reviewed Git to halt reconciliation; suspension does not stop
running workloads. Pruning is disabled and deletion orphans resources.

CNPG 1.30 on Kubernetes 1.37 is an accepted PoC exception: tested, not formally
[supported](https://cloudnative-pg.io/docs/1.30/supported_releases/).
Other platform support limits are in the [bootstrap order](../../docs/platform-bootstrap-order.md).

References: [PostgreSQL backend](https://openbao.org/docs/configuration/storage/postgresql/),
[CNPG TLS](https://cloudnative-pg.io/docs/1.30/certificates/).
