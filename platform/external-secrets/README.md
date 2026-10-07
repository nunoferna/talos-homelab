# External Secrets Operator: controller-only PoC

Merging this module into the public `main` branch activates it through the
existing Flux source. No imperative installation or private-repository change
is required. OpenTofu continues to own day-zero Cilium and Flux.

## Deliberate limits

- Official chart **2.11.0**, one controller and upstream CRDs; no webhook or
  certificate controller. Admission webhook validation is intentionally absent.
- RBAC and reconciliation are confined to `external-secrets`. This controller
  cannot read bootstrap Secrets in `flux-system` or reconcile application
  namespaces. No broad service-account TokenRequest permission is granted.
- No SecretStore, ExternalSecret, PushSecret, provider credentials, TLS Secret,
  ingress, metrics service, persistent volume or OpenBao installation.
- Cilium policy selects this namespace only: DNS to CoreDNS and API-server
  egress; node-origin health probes on TCP 8082. Provider/OpenBao egress is not
  allowed. Cilium's local-host traffic exemption may allow additional local-node
  ingress depending on the existing agent settings; this is not a host firewall.
- Backup preparation remains disconnected and suspended. This PR does not
  activate it or imply that etcd recovery has been completed.

On 2026-10-07, the operator accepted this **empty PoC** on Kubernetes 1.37.0
despite ESO 2.11's published support matrix stopping at 1.36. The chart's
`kubeVersion` constraint and an offline 1.37 render do not establish runtime
compatibility. Recheck [upstream support](https://external-secrets.io/latest/introduction/stability-support/)
before any real secret-store integration. This is not production-ready secret
management and must not hold real provider credentials yet.

## Offline validation

CI downloads the release archive and verifies SHA-256
`8199b42fe80b871c6a86233a80bb14f599fd6e1e6462c1216d836577f845e161`
before rendering with Helm 4.3.0 and Kubernetes 1.37.0 capabilities. The tests
inspect the actual rendered RBAC, security context, probes and CRDs, not only
the chart values. The runtime HelmRepository uses the official HTTPS index and
an exact version; the CI archive checksum is **not** a Flux digest pin.

To repeat locally with Helm 4.3.0, kubectl and the repository's Python tools:

```sh
eso_chart_archive="$(mktemp /tmp/eso-chart.XXXXXX)"
curl --fail --silent --show-error --location \
  https://github.com/external-secrets/external-secrets/releases/download/helm-chart-2.11.0/external-secrets-2.11.0.tgz \
  --output "$eso_chart_archive"
ESO_CHART_ARCHIVE="$eso_chart_archive" python tests/external_secrets.py
```

## After merge: read-only acceptance

Use the existing protected kubeconfig. These commands do not change the cluster:

```sh
kubectl -n flux-system get kustomization external-secrets
kubectl -n external-secrets get helmrepository,helmrelease
kubectl -n external-secrets rollout status deployment/external-secrets --timeout=5m
kubectl -n external-secrets get pods,ciliumnetworkpolicies
kubectl get crd externalsecrets.external-secrets.io secretstores.external-secrets.io
kubectl -n external-secrets get secretstores,externalsecrets
kubectl auth can-i get secrets -n flux-system \
  --as=system:serviceaccount:external-secrets:external-secrets
kubectl auth can-i create serviceaccounts/token -n external-secrets \
  --as=system:serviceaccount:external-secrets:external-secrets
kubectl -n external-secrets logs deployment/external-secrets --tail=100
```

Acceptance: both Flux resources Ready, one ready controller, CRDs established,
no stores or ExternalSecrets, both authorization checks return `no`, and no
repeated API/network/forbidden errors in controller logs. Keep log output
private; do not paste credentials if a future integration changes log contents.
If reconciliation fails, diagnose with read-only status/events; submit the fix
as a reviewed Git change, not a manual Helm upgrade or permission expansion.

## Rollback and next phase

Rollback through a reviewed Git revert of the root reference. Flux pruning
removes the child reconciliation and Helm release; the namespace is protected
from cascading deletion and CRDs have Helm's `keep` annotation. Rollback does
not remove CRDs or any persisted custom resources. Never delete CRDs as a
routine rollback: doing so deletes their custom resources cluster-wide.

Next: decide and validate persistent storage without modifying the Talos OS
disk in place, then review persistent OpenBao with TLS and independent recovery
material. Only afterwards review ESO admission validation/certificate RBAC,
application namespace scope, dedicated Kubernetes-auth service accounts,
least-privilege TokenRequest/Bao policies and explicit Bao network access.
SOPS remains an exception for bootstrap inputs that cannot come from OpenBao.
