# Longhorn V1: shared-SSD preparation

Selected direction: Longhorn V1 on the existing Talos `/var` filesystem, with no
additional SSD, partition allocation, filesystem resize, or node rebuild.
This is a homelab PoC design with explicit compromises, not a production
availability guarantee.

## Status and merge boundary

The release is **suspended** and `resources/` is **not referenced** by
`clusters/homelab`. There is no activating Flux Kustomization. Merging this
preparation installs nothing, registers no disks, creates no volumes, and
performs no node upgrade. Do not merge the alternative Rook/Ceph preparation as
an activation step for this design.

The OpenTofu legacy-kubelet flag defaults to false. Existing installer images,
cluster identity, bootstrap resource addresses, backend, and private inventory
remain unchanged. Image Factory input under `host/` is a candidate, not a
schematic already generated or installed. There is currently no approved
Longhorn host-upgrade/delivery playbook; creating that automation is a required
next stage, not a manual-command workaround.

## Compatibility decision before activation

Candidate chart and application: **Longhorn 1.13.0**. The official chart index
publishes archive SHA-256
`e57f010d2a8bcf0da5b8b03ffecf49c5bc35ddc2663588ce8f22b7567b6133ed`.
Its chart declares Kubernetes `>=1.34.0-0`. The best-practice page publishes a
tested Kubernetes matrix through 1.36 and lists Talos 1.13.4 as verified.
The cluster was read-only verified as Talos 1.14.1 / Kubernetes 1.37.0 on
2026-10-12. A passing Helm render on 1.37 is **not** a compatibility certification.

On 2026-10-12 the operator explicitly accepted Longhorn 1.13.0 on Talos
1.14.1 / Kubernetes 1.37.0 for **disposable-data PoC only**. This is not a
tested-matrix certification or permission to store real OpenBao/application
secrets. This acceptance does not approve a downgrade, OS upgrade, configuration
delivery, or storage activation; those retain their separate review gates.

The read-only `management/ansible/talos-longhorn-host-preview.yaml` checks the
private target contract, protected local credential metadata, exact cluster and
node identities/versions, and native cluster health before asking **one** named
node to preview the committed kubelet patch. It never applies configuration,
upgrades, labels a node, registers a schematic, or touches OpenTofu state. Native
preview output is suppressed because it can contain machine secrets. Passing
this check does not prove custom kubelet settings were preserved, extensions
installed, or storage working. Reviewed full-config comparison and serial
delivery remain necessary. The private repository holds targets and the first
selected node; do not commit site-specific addresses here.

The operator selected protected Mac credentials and reviewed local Ansible for
this PoC on 2026-10-12. Do not reuse the Pi's Kubernetes OIDC identity for Talos,
or distribute Talos credentials to the runner/GitHub. The current implementation
is read-only; approval-gated local delivery remains a separate stage. No new
credentials are required for the preview.

The early Talos 1.14 alpha `noexec` warning for `/var` was reverted before stable
1.14.0 (release changelog: `6fa811a0d`, drop `noexec` for KUBELET, EPHEMERAL and
CRI). Do not blindly disable `mount.secure`: inspect actual mounts and validate
the exact release. No mount-security weakening is included here.

## Host prerequisites: code first

Each approved storage node needs `siderolabs/iscsi-tools` and
`siderolabs/util-linux-tools`. The current nodes do not have these extensions.

1. Review `host/image-factory-schematic.yaml` against the existing private
   schematic. Preserve Secure Boot, overlays, kernel arguments, and any existing
   extensions; this candidate is not permission to replace other customization.
2. Implement reviewed, approval-gated local Ansible with private inputs that records the exact
   Image Factory schematic and installer image, performs a reviewed one-node
   Talos upgrade, and stops unless API, etcd, Cilium, and Flux remain healthy.
   Keep Talos at the reviewed version; installing extensions does not require
   an unrelated OS-version bump. No all-node simultaneous rollout.
3. Review the **kubelet schema conversion** before setting
   `enable_longhorn_legacy_kubelet=true` in private inputs. The upstream legacy
   `.machine.kubelet` patch alone fails native validation with the generated
   Talos 1.14 `KubeletConfig`. Version-pinned source confirms that document's
   `ExtraMounts()` returns nil and its conflict validator rejects mixing the two
   schemas. The opt-in template removes only that document and recreates its
   generated defaults in the supported legacy schema: same kubelet image,
   default runtime seccomp enabled, and static manifests directory disabled,
   plus the Longhorn bind mount. Preserve any custom kubelet settings before
   opting in; do not treat this as an additive mount-only change. Use
   the existing encrypted-state OpenTofu plan path. Reject any identity/bootstrap
   replacement, disk provisioning, or unexpected machine-configuration change.
   A state apply only updates rendered outputs; it does not install extensions
   or deliver the bind mount. Do not reactivate deferred etcd-backup access.
4. Validate full rendered configurations with matching `talosctl`, then deliver
   them via separately reviewed, serial automation. The standalone template
   is not a complete machine configuration. Compare existing extra mounts to
   ensure none are lost. Confirm bidirectional mount propagation, data-path
   availability, iSCSI service, and trimming support before starting Longhorn.
5. Keep the old reviewed configuration and installer image as rollback evidence.
   Do not remove mount/extension prerequisites once they serve real volumes.

The upstream `UserVolumeConfig` example provisions a partition; free bytes
inside XFS are not unallocated disk space. Do **not** apply that example to the
existing whole-disk EPHEMERAL layout. `longhorn-legacy-kubelet.yaml.tftpl` exposes
the existing `/var/lib/longhorn` directory. It creates no `UserVolumeConfig`,
`RawVolumeConfig`, disk wipe, or filesystem-size change.

## Storage and security boundaries

- V1 only; V2 is disabled. No SPDK, huge-page reservation, or raw devices.
- Default disks are created only on explicitly labeled nodes. Add both
  `homelab.storage/longhorn=true` (component placement) and
  `node.longhorn.io/create-default-disk=true` (disk registration) through reviewed private node
  configuration for approved nodes only; do not manually label live nodes.
  The chart's global node selector and system-managed component selector require
  the first label; runtime placement still needs verification. A disk-registration
  label alone does not restrict where all privileged components run.
- Default disk reservation: 30%; overprovisioning: 100%; minimum available:
  25%. These are scheduling guards, **not quotas**. Snapshots and OS image/log
  growth can still exhaust the shared filesystem. Require small PVCs, namespace
  storage quotas, and capacity alerts before real application data. Start with
  one 1 GiB disposable claim; no application PVC is included in preparation.
- Three replicas, hard node separation, no creation with degraded availability,
  and one concurrent replica rebuild per node. With three storage nodes, losing
  one leaves only two independent hosts; three copies cannot be restored until
  a third host returns. Benchmark rebuild I/O against control-plane etcd latency.
- Snapshot count is limited to eight, but count is not a byte limit and no
  snapshot/backup schedule is installed. No R2 credentials or backup target.
- Non-default `longhorn-rwo` StorageClass: V1, three replicas,
  `WaitForFirstConsumer`, and `Retain`. The chart-managed default class is off.
  Retain prevents automatic PV data deletion after claim release, not all
  possible operator/chart/controller deletion paths.
- Namespace and HelmRelease pruning are disabled; chart CRDs receive
  `helm.sh/resource-policy: keep`. Uninstallation confirmation stays false.
  These safeguards are not authorization to delete releases or CRDs.
  The upstream chart includes post-upgrade and pre-delete hook Jobs; offline
  tests allow only those reviewed hooks. The uninstall hook uses `--force`
  (volumes-in-use override), but version-pinned controller source still checks
  the deleting-confirmation flag first. This is not a safe automatic rollback.
- Longhorn needs privileged host access and cluster-scoped RBAC. This is not
  equivalent to the namespace-scoped ESO controller. CSI controller-side Secret
  reads are disabled for this unencrypted PoC, but that flag does not prove
  every Longhorn role lacks Secret access. Review actual rendered RBAC.
- The candidate Cilium policy allows the storage namespace, DNS/API and node
  entities. Node-entity traffic is deliberately broad for dynamic storage ports
  and host initiators. It is not an application-level least-privilege proof;
  host-network components are not covered like ordinary endpoints. Verify
  webhook/CSI/iSCSI paths and observe flows before activation. Do not disable
  admission validation or broaden to `world` to make an install pass.
- UI/API services are ClusterIP only, with no ingress, HTTPRoute or public
  endpoint. Chart components are version-tagged by the checksum-reviewed chart;
  images are not digest-pinned. CI archive verification is not runtime Flux
  archive digest enforcement. Re-review those boundaries for production use.

## Activation and acceptance: separate reviewed stage

After compatibility and host prerequisites pass, prepare an activation PR that
adds a bounded Flux Kustomization, unsuspends the release, includes placement and
capacity controls, and health-checks the HelmRelease. Do not simply resync this
disconnected directory or manually install Helm. Keep the private-reconciler
RBAC boundary unchanged; public generic storage resources must not require
granting the private ConfigMap-only reconciler cluster-admin access.

Add the disposable 1 GiB RWO PVC and fixture workload through Git. Their normal
container commands should write, sync and verify known non-sensitive data; no
operator `kubectl exec` writes. A Bound claim alone is insufficient: require
healthy CSI controllers, three storage nodes, three distinct healthy replicas,
successful attachment/mount/read/write, pod-recreation persistence, and healthy
API/etcd/Cilium/Flux. Record failures as evidence rather than assuming static
tests prove runtime safety. Destructive node/disk failure tests need a separate
reviewed drill. OpenBao and real secrets stay gated until storage acceptance.

Replication and in-cluster snapshots do not protect against loss of the cluster,
accidental deletion, or disk resets. The deferred etcd recovery work remains
deferred; volume backups and native OpenBao Raft snapshots are separate future
requirements before storing irreplaceable secrets. No hourly backup ceremony is
introduced by this preparation.

## Read-only operator checks

Run from a checkout with protected configs. Set paths locally, never commit them.
No mutations or secret reads are required by these commands.

```bash
export KUBECONFIG=/absolute/path/to/protected/kubeconfig
export TALOSCONFIG=/absolute/path/to/protected/talosconfig
storage_node_ips="$(kubectl get nodes -o json | jq -r \
  '[.items[].status.addresses[] | select(.type == "InternalIP") | .address] | join(",")')"
test -n "$storage_node_ips"
kubectl get nodes
kubectl get storageclasses,persistentvolumes,persistentvolumeclaims -A
talosctl --nodes "$storage_node_ips" get extensions
talosctl --nodes "$storage_node_ips" get volumestatus
talosctl --nodes "$storage_node_ips" mounts
```

After reviewed activation only:

```bash
kubectl -n longhorn-system get helmreleases,pods
kubectl -n longhorn-system get nodes.longhorn.io
kubectl -n longhorn-system get volumes.longhorn.io,replicas.longhorn.io
kubectl -n longhorn-system get events --field-selector type=Warning
kubectl -n longhorn-system get ciliumnetworkpolicies,ciliumendpoints
```

Before activation, rollback is just reverting the preparation commit: it owns
no live resources. After activation, suspension does not stop running workloads,
and reverting a root reference is not a safe storage-uninstall procedure. Review
any removal with volume inventory, recovery evidence and explicit approval;
do not wipe disks, delete CRDs, or enable uninstall confirmation casually.

## References

- [Longhorn Talos integration](https://longhorn.io/docs/1.13.0/advanced-resources/os-distro-specific/talos-linux-support/)
- [Longhorn production and OS-disk guidance](https://longhorn.io/docs/1.13.0/best-practices/)
- [Disk reservations and enforcement limitations](https://longhorn.io/docs/1.13.0/nodes-and-volumes/nodes/multidisk/)
- [Longhorn chart index](https://charts.longhorn.io/index.yaml)
- [Talos 1.14 stable release](https://github.com/siderolabs/talos/releases/tag/v1.14.0)
- [Talos 1.14.1 kubelet schema and conflict validator](https://github.com/siderolabs/talos/blob/v1.14.1/pkg/machinery/config/types/k8s/kubelet.go)
- [Longhorn uninstall guard](https://github.com/longhorn/longhorn-manager/blob/v1.13.0/controller/uninstall_controller.go)
- [Longhorn on Talos](https://docs.siderolabs.com/kubernetes-guides/csi/longhorn)
