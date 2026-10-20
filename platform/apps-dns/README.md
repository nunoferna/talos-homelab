# Application DNS

Separate CoreDNS for `apps.internal`, using the [official Helm chart](https://github.com/coredns/helm)
1.49.0 / CoreDNS 1.14.7. This is not the Talos-owned `kube-system/coredns` deployment.

Flux enables `apps-dns-inputs` before `apps-dns` using an explicit dependency.
The ConfigMap-only private-input identity supplies the reserved LAN address,
interface, client CIDR, SOA serial and HTTPS gateway address. The public workload
then deploys DNS and advertises its reserved address. There is no dependency on
the suspended TLS gateway inputs.

Two replicas serve explicit records
over LAN TCP/UDP 53, using Cilium IPAM/L2 with exact Service selectors. Pods bind
1053 with only `NET_BIND_SERVICE`, required by the official binary's file
capability even on a high port. No API RBAC or service-account tokens. Network policy
permits LAN DNS and node-forwarded requests/probes, and denies egress. There is
no recursive forwarding, Kubernetes plugin, wildcard or AAAA record. Node SNAT
means the policy cannot distinguish the original LAN client on every path;
router WAN protections still matter. Two replicas do not survive cluster loss.

The Mac Ansible resolver defaults to read-only preview; explicit enable checks
TCP/UDP answers before changing only `/etc/resolver/apps.internal`. The private
apps-DNS runbook contains operator commands. Router/default DNS and the Pi stay
unchanged. Pods cannot resolve this zone until a separately approved cluster
CoreDNS ownership handoff adds suffix-only forwarding; Keycloak/OIDC is not ready.

Change records through reviewed Git commits and bump the private SOA serial.
Rollback clients first, then withdraw DNS resources through Git. Suspending Flux
alone does not stop existing DNS or withdraw its address. Retain cluster DNS.
