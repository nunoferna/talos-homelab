# OpenBao + ESO: node-local persistent PoC

Selected scope: one normal OpenBao server, one retained node-local volume, TLS,
and a namespace-scoped ESO test. No Longhorn, Ceph, PostgreSQL, dev mode,
auto-unseal service, snapshot jobs, backup credentials, repartitioning or OS
upgrade. This is disposable-test data only, not an HA or recoverable platform.

## This PR does not deploy

`platform/openbao` is not referenced by `clusters/homelab`. The server
Kustomization, HelmRelease, private TLS input reconciliation and ESO adapter are
also suspended. Merging prepares code only. Existing ESO and its empty-controller
RBAC/network policy remain unchanged. Do not merge the alternative storage PRs
as dependencies of this design. Do not broaden the existing private proof role.

OpenBao chart 0.30.3 / application 2.7.1 is pinned. Official archive SHA-256:
`d50ed31b8305f430df308c342dd3c1efa877222380e99cb480f74f070d6beaa8`.
CI checks the actual chart with Helm 4.3.0 and validates the host patch with
Talos 1.14.1. The CI archive checksum is not runtime Flux digest enforcement;
application image tags are version-pinned, not digest-pinned. A successful
render is not a tested Kubernetes compatibility
guarantee. The previous empty ESO PoC acceptance is not proof that its provider
integration works; prove TLS, auth, policy and refresh using only the fixture.

## Host and volume

Private inputs choose exactly one existing inventory node. OpenTofu's
`openbao_local_storage_node` defaults to empty (off). When selected, only that
node receives the `/var/mnt/openbao-poc` bind mount. Talos 1.14.1 mounts the
parent `/var/mnt` read-only in kubelet; directory-backed storage on the existing
filesystem therefore needs this narrow writable exception. Native kubelet
startup creates the source directory. No hostPath helper, privileged pod or
new partition is needed. The local PV's normal filesystem group handling must
be verified at runtime, not assumed from a Bound claim.

The Talos generator uses a `KubeletConfig` document whose `ExtraMounts()` is
empty. The opt-in patch removes that document and reproduces its defaults in
the still-supported legacy schema, preserving the kubelet image, runtime
seccomp and disabled static manifest directory. This is a **schema conversion**,
not an additive patch: privately compare current and candidate full configs,
preserve custom settings/mounts and obtain a reviewed plan before delivery.

Runtime: OpenTofu 1.12.6, Talos provider 0.12.0, existing encrypted R2 Talos
state; local protected Mac credentials. Backend, identity/bootstrap addresses,
installer image and other node configs must remain unchanged. Do not enable
deferred backup API access. Native validation commands:

```sh
tofu fmt -check -diff -recursive infrastructure
tofu -chdir=infrastructure/talos init -backend=false -input=false
tofu -chdir=infrastructure/talos validate
```

An eventual encrypted `plan -out` needs private inputs and a one-node config
delta review. Applying rendered outputs does not deliver them to a node. Keep
delivery separately approved and code-driven with native dry-run, try-mode and
API/etcd/Cilium/Flux checks. No direct manual node-mutation commands are required
by this preparation. Native try-mode behavior must be checked before use; do
not infer that a schema conversion is safely hot-reloadable.

The non-default `openbao-local` class has no provisioner. Its pre-reserved 2 GiB
PV serves only `openbao/data-openbao-0`, with hard node affinity. PV, PVC and
namespace retention are deliberate. **2 GiB is a binding declaration, not an
enforced directory quota**; data shares the OS/etcd filesystem. Keep writes tiny
and inspect disk growth. Node outage makes OpenBao unavailable; disk loss loses
its data. Do not change the private node setting to relocate existing data.

## OpenBao bootstrap

The server is non-root, drops capabilities, uses runtime seccomp and a
read-only root filesystem. It has no injector, CSI driver, ingress, UI service,
automated snapshots or Kubernetes Secret-reading role. Its Kubernetes role
permits only TokenReview creation for authentication. Mount a private
`openbao-tls` Secret containing `tls.crt`, `tls.key`, `ca.crt`; the CA private
key must not be included. Required certificate SANs include the OpenBao service
and pod DNS names and 127.0.0.1 for the protected local bootstrap tunnel.
Put the public CA certificate in `external-secrets/openbao-ca` as `ca.crt`.

TLS is an unavoidable bootstrap input, not a new recovery project. Use a
reviewed private SOPS exception and the existing Flux age identity; no private
key or root token goes in public Git, Helm values or a ConfigMap. The dedicated
private input role can create Secrets only in `openbao` and ConfigMaps only in
`external-secrets`; ordinary create cannot be name-restricted by Kubernetes.
Subsequent read/update/patch is name-restricted, with no delete/list/watch.
Do not turn that role into cluster-admin or expand the proof reconciler.

OpenBao starts **sealed/uninitialized**. Helm uses disableWait only to allow
installation of a normally sealed server, with zero remediation retries; Helm
Ready does not prove application readiness. Readiness remains false while
sealed. Liveness accepts sealed/uninitialized responses to avoid a restart loop.
OnDelete prevents an automatic update from silently resealing this single pod;
upgrades require a separate reviewed pod-replacement operation and unseal.

Initialization/unseal material remains necessary to operate OpenBao, even
without backups. Keep it outside Git on the protected Mac; do not auto-init,
auto-unseal, embed root credentials in Jobs or log responses. Use reviewed
operator automation for initialization/unseal and the API configuration below.
Those secret-generating operator steps are not implemented or run by this PR.
TLS inputs, host delivery and unseal must pass before server/adapter activation.

## ESO adapter and acceptance

The existing controller still reconciles only `external-secrets`. The adapter
adds one named TokenRequest permission for `eso-openbao-poc`, not a cluster-wide
grant. ESO uses a short-lived service-account JWT with audience `openbao-poc`,
the `kubernetes-poc` auth mount, and the dedicated role in
`configuration/eso-poc-role.json`. OpenBao validates JWTs through TokenReview
using its locally projected reviewer identity, not a long-lived reviewer token
in Git. Configure the API host from the in-cluster Kubernetes service and CA.

Reviewed operator configuration must enable `kv` as KV v2 and `kubernetes-poc`
as Kubernetes auth, install `configuration/eso-poc-policy.hcl` and the role,
then seed only `kv/poc/eso-demo` with the known non-secret message
`gitops-openbao-eso-poc-v1`. The role can read exactly that data path, without
list, write or default-policy access. Do not give ESO a root token.

Cilium allows the controller identity to reach the OpenBao identity on TCP
8200, with DNS/API dependencies and node health probes. No `world` rule or
application namespace access. Node-origin ingress is broader than probe-only
authentication; Cilium's local-host exemption also remains a documented limit.
TLS/auth/ACL enforce the API boundary. Native OpenBao/Vault API compatibility
is documented by ESO, but these exact versions still require runtime testing.

Acceptance: host directory writable without changing other nodes; PVC bound to
the reserved PV; server initialized/unsealed; TLS verified (no skip-verify);
SecretStore and ExternalSecret Ready; fixture consumer verifies the expected
value without logging it; another path and another SA/namespace are denied;
refresh reflects a reviewed fixture update. Pod-replacement persistence and
re-unseal need a separately approved test, not a claim inferred from PV binding.
The fixture consumer and mutation-test automation remain a later activation step.

## Rollback

Before activation, revert preparation: it owns nothing live. After activation,
suspend reconciliation to stop new changes; suspension does not stop running
OpenBao. Do not uninstall the chart, delete PVC/PV/namespace, wipe its directory
or remove a bind mount serving existing data. Keep approved configs and plan
checksums. Any host rollback or storage removal needs explicit review; retained
volumes are not backups and this design intentionally has no restore promise.

## References

- [Talos local storage](https://docs.siderolabs.com/kubernetes-guides/csi/local-storage)
- [Version-pinned kubelet mounts](https://github.com/siderolabs/talos/blob/v1.14.1/internal/app/machined/pkg/system/services/kubelet.go)
- [OpenBao Helm](https://openbao.org/docs/platform/k8s/helm/run/)
- [OpenBao Raft](https://openbao.org/docs/configuration/storage/raft/)
- [ESO OpenBao compatibility](https://external-secrets.io/latest/provider/openbao/)
- [Kubernetes authentication](https://openbao.org/docs/auth/kubernetes/)
