# Private application gateway: preparation

Use Cilium Gateway API for `*.apps.internal`, starting with
`keycloak.apps.internal`. No separate ingress controller or OLM is needed.

1. Merge this preparation: Flux installs seven standard Gateway API 1.6.1 CRDs
   from a pinned upstream commit. CRDs are retained, never pruned as rollback.
2. Plan Cilium with `enable_gateway_api=true` through the private Pi workflow.
   Review the encrypted saved plan, then separately approve its apply. Cilium
   stays owned by OpenTofu 1.12.6 / Helm provider 3.3.0, chart 1.20.2; no upgrade.
   The flag defaults off so a fresh CNI bootstrap does not depend on Flux/CRDs.
3. Add the shared Gateway, one reserved LAN IP, a narrowly selected L2 policy,
   private-CA TLS and per-app routes in a subsequent reviewed change. No pool,
   announcement policy, Gateway, listener, route or certificate is installed yet.

LAN DNS must resolve the same issuer from browsers and pods. `apps.internal`
uses private trust, not a public Let's Encrypt certificate: distribute only the
public CA and keep signing keys independent of OpenBao. IP/DNS details and keys
stay private. Restrict route attachment to explicitly approved namespaces.

Cilium L2 announcements are beta; start with one LAN VIP and Cluster traffic
policy, not Local. Enabling the controller can roll Cilium agents/operator;
check Talos TPROXY prerequisites and native health before apply. No implicit
Talos/kernel changes, eBPF TPROXY beta opt-in or Kubernetes version changes.

Rollback: review a new plan disabling the flag, preserving the CNI release and
CRDs. Do not uninstall Cilium, delete CRDs or replay a stale plan.

References: [Cilium 1.20.2 prerequisites](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/network/servicemesh/gateway-api/installation.rst),
[Gateway API](https://gateway-api.sigs.k8s.io/),
[L2 announcements](https://docs.cilium.io/en/stable/network/l2-announcements/).
