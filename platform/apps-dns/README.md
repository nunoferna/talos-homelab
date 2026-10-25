# Application DNS

Separate CoreDNS for `apps.internal`, using the [official Helm chart](https://github.com/coredns/helm)
1.49.0 / CoreDNS 1.14.7. This is not the Talos-owned `kube-system/coredns` deployment.

Flux enables `apps-dns-inputs` before `apps-dns` using an explicit dependency.
The ConfigMap-only private-input identity supplies the reserved LAN address,
interface, client CIDR, allocated ClusterIP, SOA serial and HTTPS gateway address. The public workload
then deploys DNS and advertises its reserved address. There is no dependency on
the TLS gateway inputs.

Two replicas serve explicit records over LAN TCP/UDP 53, using Cilium IPAM/L2
with exact Service selectors. Pods bind
1053 with only `NET_BIND_SERVICE`, required by the official binary's file
capability even on a high port. No API RBAC or service-account tokens. There is
no recursive forwarding, Kubernetes plugin, wildcard or AAAA record. Explicit
records for `keycloak.apps.internal` and `kagent.apps.internal` point to the
shared gateway. DNS resolution does not activate HTTPS or expose either app. Two
replicas do not survive cluster loss.

The Service uses `loadBalancerSourceRanges` from the private LAN CIDR: Cilium
checks external source addresses at the VIP before SNAT. NodePorts remain disabled.
The existing ClusterIP is pinned for suffix-only forwarding from cluster CoreDNS.
Its ingress requires the kube-system CoreDNS labels and service account on TCP/UDP
1053; Cilium's `bpf-lb-external-clusterip=false` must remain in force.

Behind that guard, pod ingress accepts the VXLAN `world` identity only on DNS
TCP/UDP 1053, never probe ports. Node DNS/probe access stays separate. An explicit
egress deny blocks pod-initiated outbound connections; stateful DNS/probe replies
remain allowed. Verify effective ingress/egress enforcement, repeated UDP/TCP
answers and an actual non-LAN denial before declaring the boundary fully tested.
When rolling back, remove the pod's `world` allowance first; retain the Service
source-range guard until then. Never deploy that allowance without the guard.

Source ranges do not restrict in-cluster clients or directly routed Pod IPs.
Keep Pod networks unexposed and use pod policies for in-cluster access; router
WAN protections remain required. This is not original-client identity at the pod.

The Mac Ansible resolver defaults to read-only preview; explicit enable checks
TCP/UDP answers before changing only `/etc/resolver/apps.internal`. The private
apps-DNS runbook contains operator commands. Router/default DNS and the Pi stay
unchanged. [Cluster DNS configuration](../cluster-dns/README.md) adds suffix-only
forwarding while retaining the existing Talos-bootstrapped DNS workloads.

Change records through reviewed Git commits and bump the private SOA serial.
Rollback clients first, then withdraw DNS resources through Git. Suspending Flux
alone does not stop existing DNS or withdraw its address. Retain cluster DNS.
