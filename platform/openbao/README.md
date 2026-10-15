# OpenBao with PostgreSQL: single-instance PoC

OpenBao uses its official chart 0.30.3 / app 2.7.1 with PostgreSQL, not Raft.
CloudNativePG uses official operator chart 0.29.1 / operator 1.30.1 and cluster
chart 0.9.0. PostgreSQL 17.11 is pinned to a verified official image digest.
No custom database StatefulSet, new test suite or backup project.

The module remains disconnected from clusters/homelab; all three releases and
the private inputs remain suspended. Merging installs nothing. Existing ESO
is unchanged. Native Helm dependencies order operator -> database -> OpenBao.

## Existing filesystem, not disk provisioning

One PostgreSQL instance runs on cp01. Its retained local PV uses the ordinary
directory /var/mnt/openbao-poc on the existing filesystem. The default-off
Talos rendering input and local mount playbook expose only that directory.
No formatting, repartitioning, new disk, extension/image upgrade, manual
host chown or backup API access. PostgreSQL now owns that directory; do not
also use it for Raft. No initialized Raft deployment/data exists to migrate.

The non-default no-provisioner StorageClass and 4 GiB PV are reserved for
openbao/openbao-db-1 on cp01. Static binding is deliberately limited to this
one-instance PoC: no dynamic provisioning, self-healing PVC replacement or HA.
The size is NOT a filesystem quota; the database shares the OS/etcd SSD.
Keep data small. Node outage causes downtime; disk loss loses database data.

Retain policy, Flux prune protection and the CNPG Cluster's Helm keep policy
preserve data during ordinary cleanup; they are not backups. Never delete
the Cluster, namespace, PV/PVC or directory as casual rollback. Released PVs
and replacement PVCs require review. Do not relocate by changing a selector.

## Secrets and trust

The operator watches only openbao; ordinary resource permissions are
namespace-scoped, with necessary CRD/node/webhook permissions cluster-scoped.
CNPG generates openbao-db-app and its TLS PKI in Kubernetes. Database/owner
openbao is not superuser; remote superuser password access is disabled.
OpenBao consumes PGUSER/PGPASSWORD from native Secret references, never Git,
plaintext Helm values, OpenTofu outputs or a circular ESO dependency.

OpenBao uses PGSSLMODE=verify-full, the stable read-write service DNS and the
CNPG CA. Only ca.crt is projected into OpenBao, NEVER the CA signing key.
OpenBao has no data PVC; its durable state is in PostgreSQL. Serving TLS
remains the exceptional SOPS input in the existing private repository.
The obsolete site ConfigMap and its write permissions are removed.

Separate Cilium selectors isolate server, database and operator. Policies
permit database connections, instance-manager/webhook health, DNS/API access
without general world egress. No service is publicly exposed.

## Reviewed activation

1. Merge matching public/private preparation, keeping it disconnected.
2. Review a fresh cp01-only rendering plan using the existing OpenTofu 1.12.6,
   Talos provider 0.12.0 and encrypted R2 root. Identity/bootstrap, other nodes,
   installer and backup access must not change. State apply is not delivery.
3. Separately approve the local mount playbook. It compares full configs,
   protects both native streams, uses try mode and verifies the actual mount.
4. Enable the module/operator/database via reviewed Git; check CRDs, webhook,
   PVC binding, CNPG readiness, TLS identities and bounded network access.
5. Then enable private TLS reconciliation and OpenBao, followed by reviewed
   initialization/unseal. Helm Ready is not initialized/unsealed readiness.
6. Configure bounded ESO authentication only after OpenBao is healthy.

CNPG 1.30 lists Kubernetes 1.37 as tested but NOT formally supported in its
[version-specific matrix](https://cloudnative-pg.io/docs/1.30/supported_releases/).
Acknowledge the PoC exception and verify native runtime gates before activation;
this preparation does not certify compatibility or install newer CRDs.
No implicit Kubernetes upgrade/downgrade is authorized.

Talos CA rotation is operator-deferred; credentials remain on the protected
Mac, not the Pi or CI. Before activation rollback is reverting preparation.
After persistence starts, retain data and review forward fixes; never remove
a serving bind mount. Pod replacement still requires OpenBao unseal.

References: [PostgreSQL backend](https://openbao.org/docs/configuration/storage/postgresql/),
[CNPG charts](https://github.com/cloudnative-pg/charts),
[CNPG TLS](https://cloudnative-pg.io/docs/1.30/certificates/).
