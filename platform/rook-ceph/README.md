# Rook/Ceph foundation: preparation only

Rook/Ceph is the chosen long-term storage platform. This choice provides a path
to block storage (RBD), shared filesystems (CephFS) and object storage (RGW);
it does not by itself make a three-node homelab an enterprise service.
Operational capacity, failure isolation, supported versions and recovery
remain part of the design.

**Nothing here is active.** `operator/` is absent from `clusters/homelab` and its
HelmRelease is suspended. Merging this preparation does not install Rook, CSI,
Ceph, StorageClasses or volumes, and cannot consume or format a disk. ESO stays
controller-only; OpenBao is not deployed. Existing backup preparation remains
disconnected and suspended.

## Version and operator boundary

The preparation pins official Rook **1.21.0**, released 2026-10-06, with archive
SHA-256 `c070c7985deee72d7620e0377c07ce2afba28f566fbefe47bf934d00a5692cde`.
Its version-specific prerequisite documentation lists Kubernetes 1.32-1.37.
This is a newly released minor, not a runtime-validated production choice for
this cluster. Re-review its release notes, fixes and CSI/Ceph combinations at
activation rather than treating this pin as an instruction to deploy today.

The offline chart renders one Rook operator, upstream CRDs and RBAC. Discovery,
device hotplug and loop-device support are disabled. Namespace-only watching
is not the same as namespace-only RBAC: Rook needs cluster-level permissions,
and those must be reviewed before activation. No CephCluster or other Ceph
custom-resource instance is provided, so there is no disk selection to apply.
In particular, the upstream operator ClusterRole retains cross-namespace
`pods/exec` and CSI-resource management permissions even with CSI installation
disabled. This preparation does not claim that those permissions are removed.

Rook 1.21 has a separate Ceph-CSI deployment layer. Both its bundled CSI operator
and creation of CSI-operator resources are disabled here. CSI driver releases,
Ceph images and snapshot-controller prerequisites must be explicitly pinned
and validated in later work; do not copy an older all-in-one Rook tutorial.

The namespace is currently restricted for the operator-only phase. Ceph and
CSI will require an explicitly reviewed privileged storage namespace boundary.
The Cilium policy is also operator-only (DNS/API egress); extend it for the
selected Ceph/CSI architecture before introducing a CephCluster. No host-network
or blanket cluster/internet access is enabled by this preparation.

## Hard activation gates

1. **One dedicated, unused data SSD per storage node.** The Talos OS disk is
   excluded. Filesystem free space under `/var` is not a raw device. Do not
   shrink EPHEMERAL, create loopback-file OSDs, or wipe/repartition the OS disk.
   Adding a disk is a physical operator task, not a shell provisioning step.
2. **Private exact device inventory.** Record node identity, stable device
   identity, capacity, transport, partition/filesystem state and OS-disk
   exclusion. Verify that each target contains no data to preserve. A separately
   approved Ceph deployment will write to these devices; this preparation does
   not authorize that operation. Never use `useAllNodes`, `useAllDevices` or a
   broad device filter to bypass inventory. Ceph data disks remain raw; do not
   format them as a Talos filesystem UserVolume intended for Longhorn.
3. **Talos/CSI prerequisites.** Verify the actual kernel and required RBD,
   filesystem and udev facilities, kubelet socket/mount paths and privileged
   admission. If the selected configuration needs host LVM (for example OSD
   encryption), validate Talos support first. Any host prerequisites must be
   declarative, rendered and separately reviewed; no manual `modprobe`, package
   installation or machine-config patching as an implementation shortcut.
4. **Capacity and network budget.** Reserve resources for three monitors, manager
   failover, one OSD per dedicated disk, CSI and normal workloads. Shared
   control-plane/storage/application nodes are a homelab compromise; leave
   headroom for recovery, not just steady-state CPU/RAM. Measure link bandwidth
   and latency and size for client, replication and rebuild traffic. Three
   nodes are the minimum footprint; during a node outage there is no fourth
   host on which to restore three independent host-level replicas.
5. **A reviewed activation PR.** Revalidate versions; review rendered RBAC;
   introduce Flux health/dependency gates, CSI and explicit private node/device
   selection; unsuspend only through Git. Private topology must not leak into
   public resources, and the current narrow private reconciler must not be
   silently granted cluster-admin to deploy Ceph. No direct Helm installation.

## Initial cluster target (not manifests yet)

- Three monitors on distinct hosts; never co-locate them to bypass scheduling.
- One OSD per dedicated SSD with host-level failure domains; suitable manager
  failover and disruption/maintenance safeguards.
- RBD block storage first, with a replicated pool size of three and minimum
  size two, a non-default StorageClass and `Retain` reclamation for important
  data. Plan usable capacity around replication plus operational free space,
  not the raw sum of disk capacities. Retain is not a backup.
- No CephFS, RGW/S3, ingress or externally accessible dashboard initially.
  Enable those only for a workload requirement with a separate review.
- No dependency on OpenBao/ESO to bootstrap Ceph credentials. Rook-generated
  Ceph credentials remain in Kubernetes; recovery material stays outside Git.
- Default-deny/policy design must account for monitors, OSDs, managers, operator
  and CSI. Some node-plugin traffic originates on hosts; a namespaced pod
  policy alone is not a complete storage/host security boundary.

Do not put a sample CephCluster in the public live root: upstream cluster-chart
defaults can select all nodes and unused devices. We intentionally provide no
cluster chart or device placeholder that could become a live disk claim.

## Acceptance before OpenBao

Activation must include a reviewed disposable RBD PVC and test workload. Code
should perform test-data writes; operator commands only inspect the result or
request an approved reconciliation. Require three in/up OSDs, monitor quorum,
the intended replicated pool and sustained `HEALTH_OK`, then confirm data
survives a workload restart/recreation against the same PVC. Separate node
failure/rebuild and restore exercises require their own approval and runbooks.
The presence of a StorageClass or a Bound PVC alone is not acceptance.

Only after storage acceptance should OpenBao receive real PVCs. OpenBao's Raft
replication and Ceph pool replication both consume resources; benchmark and
budget both layers. Native OpenBao Raft snapshots remain the preferred
application-consistent recovery artifact; a raw live-volume snapshot is not
automatically equivalent. Real production secrets require tested independent
recovery even though the earlier etcd PoC is currently deferred.

Once stateful data exists, **removing a Git reference is not a storage rollback**.
Protect the namespace, CRDs, CephCluster, pools and PVCs from routine pruning.
Never disable installed CRDs, enable destructive cleanup confirmation, uninstall
Ceph or delete pools/PVCs without a separately reviewed decommission procedure.

## Read-only commands for the hardware/prerequisite gate

Use existing protected kubeconfig/talosconfig. Replace only the node-address
placeholder with the verified addresses from private inventory; do not paste
credentials, generated machine configurations or state into terminal output.

```sh
export KUBECONFIG="$PWD/.local/generated/kubeconfig"
export TALOSCONFIG="$PWD/.local/generated/talosconfig"
rook_storage_nodes='REPLACE_WITH_COMMA_SEPARATED_VERIFIED_NODE_ADDRESSES'
kubectl get nodes -o wide
kubectl get storageclasses,persistentvolumes,persistentvolumeclaims --all-namespaces
talosctl --nodes "$rook_storage_nodes" version
talosctl --nodes "$rook_storage_nodes" get disks
talosctl --nodes "$rook_storage_nodes" get systemdisk
talosctl --nodes "$rook_storage_nodes" get discoveredvolumes
talosctl --nodes "$rook_storage_nodes" get volumestatus
talosctl --nodes "$rook_storage_nodes" mounts
```

Keep device inventory and output private. These are inspection commands, not
instructions to wipe, initialize or mount disks. No credential entry is needed
for this preparation. Offline CI verifies the reviewed chart checksum and
rendered boundaries without contacting Talos or Kubernetes.

## Primary references

- [Rook 1.21 prerequisites](https://github.com/rook/rook/blob/v1.21.0/Documentation/Getting-Started/Prerequisites/prerequisites.md)
- [Talos Rook/Ceph guide](https://docs.siderolabs.com/kubernetes-guides/csi/ceph-with-rook)
- [Rook storage architecture](https://rook.io/docs/rook/latest/Getting-Started/storage-architecture/)
- [Ceph hardware recommendations](https://docs.ceph.com/en/latest/start/hardware-recommendations/)
- [Rook operator chart](https://rook.io/docs/rook/latest/Helm-Charts/operator-chart/)
