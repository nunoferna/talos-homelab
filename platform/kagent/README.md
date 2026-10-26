# kagent PoC

Official kagent 0.10.4 charts are pinned by OCI digest. Flux installs CRDs,
waits for ESO credentials, then reconciles the application and one diagnostic agent.
The HTTPS route targets OAuth2 Proxy, with Keycloak passkey login restricted to
`/bao-operators`. Cilium restricts direct UI/controller/tool access.

The controller manages only its own namespace. A separate tool service account
can read workloads, events and logs across namespaces, with no Secret access,
exec or mutations. The server registers the read-only Kubernetes provider;
the agent selects four diagnostic tools. Bundled demo agents are disabled.
The agent runtime has no Kubernetes RBAC binding. Treat resource/log content as
untrusted input; read-only access still exposes operational data to the local model.
After changing providers, update the agent's tool-provider revision to refresh
its startup tool discovery through Flux.

Site values live in private `clusters/homelab/kagent/inputs`. Ollama requires no
API key. ESO reads UI and database credentials from OpenBao's
`kv/homelab/kagent/bootstrap`. PostgreSQL uses bounded `emptyDir` storage:
replacing its pod loses chat history. This is a single-operator PoC, without HA
or persistent sessions. Keep the Mac's Ollama endpoint available while chatting.
