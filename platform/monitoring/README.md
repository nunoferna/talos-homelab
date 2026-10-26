# Monitoring PoC

Flux installs pinned upstream charts: kube-prometheus-stack 92.14.0,
Grafana 14.1.0 and Grafana Operator 5.25.0. Prometheus keeps at most 48 hours
or 1 GB of retained blocks in a 2 GiB emptyDir. Pod replacement loses history.
Grafana's database is disposable too; dashboards, data sources and alert rules
are provisioned from Git. Collection continues when the Ollama Mac is offline.

`https://grafana.apps.internal` uses Keycloak passkeys and grants `/bao-operators`
Viewer access. A dedicated ESO controller reads only `kv/homelab/monitoring/*`.
The secret-store stage remains suspended until its one-time OpenBao reader
and Grafana credentials are configured using the private native Ansible workflow.
Then remove that suspension in Git; Flux orders the remaining rollout.

Grafana Operator reconciles a Viewer service account and its Kubernetes token
Secret after a Grafana database reset. The official Grafana MCP 2.1.1 reads that
file on each request. Rotate it by advancing the token expiry in
`grafana-identity/identity.yaml` before 2027-01-24. MCP has no public route;
Cilium permits only the kagent controller and observation runtime to connect.
Write tools and caller-selected Grafana destinations are disabled.

The pinned kagent 0.10.4 chart supplies Observability and PromQL agents. The
observability overlay restricts its tools and instructions to evidence gathering;
neither agent has Kubernetes RBAC. Changes remain human-reviewed Git changes.
Use queries such as `up`, pod restart rates and `ALERTS{alertstate="firing"}`.
Watchdog deliberately fires continuously. There are no external notifications.

Initially collected: API server, nodes, Kubernetes objects,
CoreDNS, Flux and kagent tools. Kubelet/cAdvisor scraping is deferred until its
TLS trust is resolved; pod CPU/memory charts will lack samples meanwhile.
Talos etcd/controller-manager/scheduler and Cilium-specific
metrics are excluded until their endpoints are configured separately. Node
exporter alone uses a privileged namespace for read-only host mounts; its
network is isolated and it does not use host networking or host PID access.

The chart's checksum-pinned upstream certificate-generation jobs bootstrap
its TLS admission webhook, with failurePolicy Fail. Their temporary chart RBAC
is removed after successful hooks. The gateway-only cert-manager scope is
unchanged. Default alert and recording rules are enabled after the verified
first certificate bootstrap.
