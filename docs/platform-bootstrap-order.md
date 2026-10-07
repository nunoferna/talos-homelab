# Platform bootstrap order

The platform is built in dependency order. A higher layer must not be required
to recover a lower layer.

1. **Cilium CNI** provides pod networking and policy enforcement.
2. **Flux** reconciles the public `clusters/homelab` root. A separate
   authenticated source may later reconcile sensitive resources from the
   private repository, but Flux never owns Cilium or its own day-zero install.
3. **Persistent storage** supplies tested failure and snapshot semantics.
4. **OpenBao** runs as a three-replica integrated-Raft service with TLS,
   anti-affinity, a disruption budget, audit logging, and one persistent volume
   per replica.
5. **External Secrets Operator** authenticates to OpenBao using Kubernetes
   service accounts and namespace-scoped policies.
6. **SOPS exceptions** cover only allowlisted bootstrap secrets that cannot be
   sourced from OpenBao.
7. **Applications and policies** are introduced namespace by namespace.

An empty, namespace-scoped ESO controller can be installed independently before
storage or OpenBao. The [controller-only PoC](../platform/external-secrets/README.md)
does exactly that; it does not move real secret-store integration ahead of its
dependencies. Rook/Ceph is the selected storage direction, but its
[preparation](../platform/rook-ceph/README.md) is disconnected and suspended
pending dedicated data disks and prerequisite validation. OpenBao is not deployed.
Etcd backup work is deferred, not completed, and remains inactive.

## Why Cilium precedes Flux

Flux controllers require working pod networking. Cilium is therefore a day-0
component permanently owned by a dedicated OpenTofu root and encrypted state.
Validate Cilium before bootstrapping Flux; do not create a Flux `HelmRelease`
for it or allow two reconcilers to own the same Helm release.

Use standard Kubernetes `NetworkPolicy` when it expresses the requirement and
`CiliumNetworkPolicy` only for Cilium-specific features such as FQDN or layer-7
rules. Begin with policy enforcement disabled during migration, observe flows,
allow DNS and required control-plane dependencies, and introduce default-deny
one namespace at a time.

## Historical existing-cluster migration gate

The original cluster used Flannel and kube-proxy. Cilium is now installed via
OpenTofu; this migration checklist is retained for a future rebuild, not as a
description of today's CNI. Replacing either is a high-impact change:

1. Pin a stable Cilium release whose tested matrix includes the cluster's
   Kubernetes version.
2. Record the current CNI, kube-proxy, pod/service CIDRs, node health, and
   control-plane reachability.
3. Render and review Talos machine configuration changes; do not deliver them
   as part of an ordinary OpenTofu apply.
4. Follow Cilium's dual-overlay migration procedure with a distinct temporary
   pod CIDR and encapsulation port. Migrate one node at a time.
5. Confirm every pod is Cilium-managed before removing Flannel.
6. Move to kube-proxy replacement only after Cilium networking is healthy, then
   disable kube-proxy in Talos in a separate reviewed stage.
7. Run Cilium connectivity tests, DNS/API checks, cross-node traffic checks, and
   node-reboot checks before enabling policy enforcement.

Do not combine CNI replacement, kube-proxy removal, Flux bootstrap, and network
default-deny into one change. Each stage needs an independently observable
health gate and rollback point.

## Compatibility gate for this cluster

The cluster currently runs Kubernetes 1.37.0. At the time this decision was
recorded, stable Cilium 1.20.2 guaranteed compatibility through Kubernetes 1.36;
Cilium 1.21 had Kubernetes 1.37 support in prerelease builds only. The operator
separately accepted continuing with stable Cilium 1.20.2; that acceptance is not
an upstream compatibility guarantee. Recheck the supported matrix before
persistent OpenBao or make a separately reviewed cluster-version decision.

ESO 2.11 likewise publishes support through Kubernetes 1.36. The operator
accepted a controller-only PoC on 1.37 on 2026-10-07, without secret stores or
real credentials. Passing static checks is not a runtime compatibility result.

## OpenBao and SOPS rules

OpenBao must not depend on ESO or on secrets that only OpenBao can provide. Its
initial TLS and initialization path must be recoverable independently. Store
unseal/recovery material outside Git in at least two independently controlled
encrypted locations.

The SOPS allowlist should normally be limited to bootstrap credentials for
storage, networking, or secret-store initialization when no workload identity
path exists. CI must reject unencrypted `Secret` values and SOPS files outside
the approved paths.
