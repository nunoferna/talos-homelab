# Pod DNS forwarding

Flux owns only `kube-system/coredns` configuration. The existing CoreDNS
Deployment, Service, image, replicas and RBAC stay bootstrapped by Talos.
Talos 1.14.1's manifest applier skips inventory entries and existing resources;
it does not continually overwrite this ConfigMap. Preserve its bootstrap
inventory annotation as provenance. Recheck this boundary when upgrading Talos.

The stock Corefile is preserved, with one `apps.internal` server block forwarding
to the application DNS Service's pinned ClusterIP. Service discovery and default
upstream DNS retain their existing settings. The reload plugin loads the change
without replacing DNS pods.

Application DNS enables its existing ClusterIP frontend and permits only the
kube-system CoreDNS service account/pod labels on UDP/TCP 1053. LAN VIP source
ranges remain unchanged; Cilium's `bpf-lb-external-clusterip=false` keeps
ClusterIPs internal. That setting is a prerequisite for this configuration.

Merge the private ClusterIP input first. The scoped Flux service account manages
only the CoreDNS ConfigMap and reads Deployment health. Pruning, deletion and
forced replacement are disabled. After merge verify both application names,
`kubernetes.default.svc.cluster.local` and an external name from existing pods;
inspect CoreDNS reload logs and confirm the Service/Deployment UIDs are unchanged.

Rollback removes the conditional block through Git while retaining stock DNS.
Sources: [Talos 1.14.1 manifest application](https://github.com/siderolabs/talos/blob/v1.14.1/internal/app/machined/pkg/controllers/k8s/manifest_apply.go),
[CoreDNS forwarding](https://coredns.io/plugins/forward/).
