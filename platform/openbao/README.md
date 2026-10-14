# OpenBao: official Helm chart, persistent single-instance PoC

OpenBao is installed from its [official Helm repository](https://openbao.github.io/openbao-helm)
using one Flux HelmRepository and HelmRelease. No custom operator or copied
StatefulSet. Chart 0.30.3 pins OpenBao 2.7.1; omitted values use that exact chart's
defaults. No Longhorn, Ceph, PostgreSQL, dev mode or backup automation.

## Small GitOps structure

- namespace.yaml: retained restricted namespace.
- source.yaml and release.yaml: official repository and chart values.
- network-policy.yaml: private API, DNS/API dependencies and node health probes.
- private-inputs.yaml: reuse the existing homelab-private Git source to deliver
  site values and encrypted TLS into openbao, with one namespace-scoped identity.
- kustomization.yaml: assemble the module.

The module is not referenced by clusters/homelab. The release and private inputs
remain suspended. Merging installs nothing. Existing ESO and the private proof
role are unchanged. Configure the ESO adapter only after OpenBao is running;
the speculative adapter, new Git source and multiple phase bridges were removed.

## Only necessary values

The private openbao-site ConfigMap supplies server.nodeSelector through Helm
valuesFrom. The official chart's extraObjects feature creates the non-default
local StorageClass and retained PV, using the same node selector for PV affinity.
The 2 GiB PV is reserved for openbao/data-openbao-0. keep annotations preserve
the PV/class on Helm deletion; the StatefulSet also retains its PVC.

**A directory PV does not enforce a 2 GiB quota.** It shares the OS/etcd disk.
Keep data small. Node outage means downtime; disk loss loses data. Do not change
the node value to relocate existing data or uninstall as routine rollback.

The other overrides enable TLS, one-member Raft, bounded resources, restricted
container settings and sealed-safe health behavior. API addresses use chart
values, not a custom renderer. One small post-render corrects the upstream
readiness command to verify TLS. The chart needs writable temporary storage
while its root filesystem is read-only. The API/UI is not exposed publicly.

## Host prerequisite, unchanged

Talos 1.14.1 exposes /var/mnt read-only to kubelet. The default-off OpenTofu input
openbao_local_storage_node adds only /var/mnt/openbao-poc on one selected node.
It requires a legacy kubelet schema conversion: compare private full configs
and preserve any custom settings before delivery. No repartitioning, extension,
installer change, OS upgrade or backup API access is needed.

Use the existing OpenTofu 1.12.6 / Talos provider 0.12.0 encrypted R2 root and
protected Mac credentials. Identity/bootstrap and other nodes must stay unchanged.
See [the Talos root](../../infrastructure/talos/README.md) for validation/plan
commands. Rendering/state apply does not deliver config. Keep native dry-run,
reviewed plan and one-node delivery approval separate. Do not remove the mount
once it serves data.

## Bootstrap, then ESO

1. Review and deliver the one-node mount through code.
2. Add private site values and an encrypted openbao-tls Secret in
   clusters/homelab/openbao/inputs of the private repository. It needs tls.crt,
   tls.key and ca.crt, never the CA private key. Certificate SANs must include
   the service/pod DNS names and 127.0.0.1 for local verified bootstrap.
3. Activate this module, its private inputs and HelmRelease through reviewed Git.
4. Initialize/unseal using protected local operator material, then connect the
   existing ESO controller with namespace/SA-bound auth and narrow permissions.

Helm installs OpenBao but does not initialize or unseal it. disableWait permits
installation of a sealed server; Helm Ready is not application readiness.
OnDelete uses the chart default: future pod replacement must account for unseal.
No root token, unseal key or real application secret belongs in Git or Helm values.
TLS/init/unseal automation is not implemented by this preparation.

The private input identity can create ConfigMaps/Secrets only in openbao;
Kubernetes cannot name-restrict ordinary create. Later writes/read are restricted
to openbao-site/openbao-tls, with no delete/list/watch. No cluster-admin grant or
change to the existing proof role.

This configuration does not certify runtime/version compatibility. Before
activation rollback is reverting preparation. After
activation, do not delete the namespace, PVC/PV, directory or a serving mount.

[Official Helm installation and initialization](https://openbao.org/docs/platform/k8s/helm/run/)
