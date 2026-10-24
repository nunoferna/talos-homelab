# Internal apps gateway

Preparation only: both activation Kustomizations are suspended. Merging creates no
Gateway, IP pool, L2 policy or application route.

Public Git owns the HTTPS-only shared Gateway and narrowly selected Cilium
networking resources. Private Git supplies the reserved IPv4/interface settings
and the public OpenBao TLS CA. OpenBao PKI and cert-manager will own the
`apps-internal-tls` leaf Secret; the root signing key stays outside the cluster.
See [application PKI](../apps-pki/README.md). There is no HTTP listener, catch-all
route, or Keycloak deployment.

Activate only in a later reviewed PR, after certificate issuance, client trust,
and Mac/pod DNS checks. The PKI dependency requires the Issuer and Certificate Ready; Gateway
readiness requires current-generation Accepted and Programmed conditions.
Application namespaces must explicitly opt in with
`apps.internal/gateway-access: 'true'` before attaching an HTTPRoute.

Cilium L2 is beta; the interface selector is not a firewall. No WAN forwarding
is configured. Keep the existing router firewall; DNS is not an access control.
Rollback requires a reviewed removal of gateway exposure, not deleting Cilium,
its CRDs, or the protected gateway namespace. Suspension alone does not withdraw
an address after activation.

References: [Cilium L2](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/network/l2-announcements.rst),
[IP allocation](https://github.com/cilium/cilium/blob/v1.20.2/Documentation/network/lb-ipam.rst).
