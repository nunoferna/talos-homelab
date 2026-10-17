# Platform ownership and order

1. **OpenTofu:** Talos rendering, day-zero Cilium and Flux. Do not give Flux
   ownership of the same Helm releases. Talos delivery is separately reviewed
   local Ansible, not an automatic consequence of state apply.
2. **Flux:** public `clusters/homelab` resources and narrowly scoped private
   inputs through an authenticated, read-only Git source.
3. **PostgreSQL → OpenBao:** official charts, verified TLS, retained local
   PostgreSQL data. See [architecture and limits](../platform/openbao/README.md).
4. **ESO → applications:** bounded Kubernetes authentication, namespace stores
   and per-application policies. See [current scope and next gate](../platform/external-secrets/README.md).
5. **SOPS exceptions:** only allowlisted bootstrap inputs that cannot come from
   OpenBao. Unseal/root material stays outside Git and the cluster.

An empty ESO controller can run before OpenBao; secret-provider integration
cannot. No component should depend on secrets it must itself make available.
Public Git contains resources, not credentials, private inventory or operator
records. Make changes through reviewed commits, with read-only verification.

## PoC limits

No HA or completed database/etcd recovery. Longhorn/Ceph and backup work remain
deferred. Retained volumes and encrypted key custody are not database backups.
Review availability, audit logging, non-root operator access and recovery
before using real application secrets.

Kubernetes is 1.37. Cilium 1.20.2's recorded compatibility exception and CNPG
1.30's tested-but-not-formally-supported exception were operator-accepted for
this PoC. On 2026-10-17 the operator also accepted ESO's Kubernetes 1.37
compatibility exception for disposable-data provider integration. No access
is enabled by that decision or the controller upgrade. Recheck upstream
matrices before expanding scope; static rendering and readiness do not certify
production compatibility. No cluster version change is implied.
