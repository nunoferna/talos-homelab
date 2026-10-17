# OpenBao with PostgreSQL: single-instance PoC

OpenBao uses its official chart 0.30.3 / app 2.7.1 with PostgreSQL, not Raft.
CloudNativePG uses official operator chart 0.29.1 / operator 1.30.1 and cluster
chart 0.9.0. PostgreSQL 17.11 is pinned to a verified official image digest.
No custom database StatefulSet, new test suite or backup project.

The public root owns a dedicated Flux Kustomization for this module, matching
the ESO reconciliation pattern. Following PostgreSQL acceptance, this stage
enables OpenBao and its existing encrypted private TLS input. CNPG, database,
retained local storage and bounded policies are unchanged. Existing ESO is
unchanged. Native Helm dependencies order operator -> database -> OpenBao.
OpenBao is normal server mode, not dev mode; initialization/unseal is separate.

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

1. Complete public/private preparation and separately approved cp01-only host
   rendering/delivery using the existing OpenTofu 1.12.6, Talos provider 0.12.0
   and encrypted R2 root. Require unchanged identity/bootstrap and other nodes,
   a writable /var/mnt/openbao-poc in the running kubelet and no-op planning.
   Keep actual rollout evidence in protected operator custody, not public Git.
2. Before merging activation, acknowledge the CNPG/Kubernetes PoC support
   exception below. No cluster version change is included.
3. Merge PostgreSQL-first activation. Flux installs the official charts;
   no manual Helm install or imperative resource creation is needed. The child
   reconciliation checks both HelmReleases, the CNPG Cluster and its PVC.
4. Verify live CRDs/webhook, cp01 placement, exact retained PVC/PV binding,
   CNPG Ready, generated TLS identities and bounded network access. Native
   readiness is necessary but does not certify the unsupported combination.
5. After database acceptance, merge this private TLS/OpenBao activation. Flux
   decrypts the existing TLS input using its existing SOPS identity and deploys
   the official OpenBao chart. No new ciphertext or keys are generated here.
   The kubelet will not start the container without the required TLS/database
   Secret mounts; the two Flux controllers may reconcile in either order.
   Child health checks require successful TLS reconciliation and Helm install,
   not initialized/unsealed readiness. Then review initialization/unseal.
6. Configure bounded ESO authentication only after OpenBao is healthy.

CNPG 1.30 lists Kubernetes 1.37 as tested but NOT formally supported in its
[version-specific matrix](https://cloudnative-pg.io/docs/1.30/supported_releases/).
Acknowledge the PoC exception before merging activation and verify native
runtime gates before enabling OpenBao. This does not certify compatibility.
No implicit Kubernetes upgrade/downgrade is authorized.

Talos CA rotation is operator-deferred; credentials remain on the protected
Mac, not the Pi or CI. To halt a failed rollout, commit suspension of the two
database HelmReleases and inspect read-only diagnostics; suspension does not
stop already-running workloads. Removing this child reconciliation or reverting
the root reference is not an uninstall: prune is false and deletion orphans
resources. Retain data and review forward fixes; never delete the namespace,
Cluster, PVC/PV or serving bind mount as rollback. Pod replacement will still
require OpenBao unseal once OpenBao is activated.

## Expected first server state

Before initialization, expect initialized=false and sealed=true from the native
[bao status](https://openbao.org/docs/commands/status/) command (exit 2 for
sealed, not exit 1 for a connection/TLS error). A Running pod with 0/1 readiness
is expected. Its verified readiness probe remains failing until unseal; the
liveness probe deliberately accepts sealed/uninitialized status to avoid a
restart loop. Helm waiting is disabled for this boundary, so Helm/Flux Ready
must not be interpreted as application-ready or safe for real secrets.

After merge, verify actual database connectivity, TLS input reconciliation,
serving certificate identity, server version/storage type and stable restart
count using read-only diagnostics. Do not initialize, submit unseal shares,
create an auth mount/secret engine, or configure ESO in this activation step.
Root tokens and unseal material must stay outside Git, CI logs and chat.
The next operator change requires reviewed local automation and key custody.

References: [PostgreSQL backend](https://openbao.org/docs/configuration/storage/postgresql/),
[CNPG charts](https://github.com/cloudnative-pg/charts),
[CNPG TLS](https://cloudnative-pg.io/docs/1.30/certificates/).
