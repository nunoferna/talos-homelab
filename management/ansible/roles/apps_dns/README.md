# LAN apps DNS

`apps-dns.yaml` defaults to read-only preview. An explicit `apps_dns_operation=deploy`
installs checksum-pinned CoreDNS 1.14.7 as a sandboxed, non-root systemd service.
Private site input comes from `APPS_DNS_SITE_FILE`; SSH uses the existing inventory.
It binds only the configured Pi IPv4 address, serves explicit `apps.internal`
records, allows listed client networks, and has no recursive/public forwarding.
It does not alter Pi upstream DNS, DHCP, the router or Kubernetes.

`apps-dns-mac.yaml` also defaults to preview. Explicit `enable` verifies UDP/TCP
answers before writing only `/etc/resolver/apps.internal`. It refuses unmanaged
files/symlinks and never edits default resolver or trust settings. macOS native
resolution is checked with `dscacheutil`; plain `dig name` does not exercise
macOS domain-specific resolver selection. VPN/browser secure-DNS overrides may
need separate review.

Merge is preparation only; neither playbook runs automatically. Roll back Mac
selection with `apps_dns_mac_operation=disable` before stopping the dedicated Pi
service with `apps_dns_operation=stop`. Files/binary are retained; no broad cleanup.
Bump the private SOA serial when changing zone records. One Pi is a DNS SPOF.

Talos 1.14.1 currently owns cluster CoreDNS. Its pinned KubeCoreDNSConfig supports
only enabled/image, not custom zones; its ResolverConfig has no per-domain
upstream field. A reviewed ownership handoff to Flux is a separate stage. Do not
patch the live Corefile, deploy a second manager, or replace public resolvers with
the Pi. Cluster/app OIDC readiness is not achieved by the Mac resolver alone.

References: [CoreDNS release](https://github.com/coredns/coredns/releases/tag/v1.14.7),
[ACL](https://coredns.io/plugins/acl/),
[Talos schema](https://github.com/siderolabs/talos/blob/v1.14.1/pkg/machinery/config/types/k8s/coredns.go).
