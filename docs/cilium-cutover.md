# Cilium cutover

This runbook replaces Talos-managed Flannel and kube-proxy with Cilium. It is a
high-impact, cluster-wide networking operation. The Talos API and Kubernetes API
static pods remain on the host network, but ordinary pod networking and DNS may
be unavailable during the cutover.

## Pinned context

- Talos: 1.14.1
- Kubernetes: 1.37.0
- Cilium chart: 1.20.2
- OpenTofu: 1.12.6
- Talos provider: 0.12.0
- backend: encrypted and locked R2 S3-compatible state

Cilium 1.20.2's guaranteed test matrix ends at Kubernetes 1.36. The operator
explicitly accepted Kubernetes 1.37 after independent validation. Revisit this
decision before any later Cilium upgrade.

## Separation of responsibilities

OpenTofu renders the durable Talos configuration. It does not install Cilium or
deliver machine configuration to nodes. Cilium's pinned public Helm values live
in the public platform repository. Cluster-specific evidence and generated
machine configurations remain ignored or in the private live repository.

## Preconditions

1. All three nodes, etcd members, control-plane static pods, Flannel pods, and
   kube-proxy pods are healthy.
2. The workstation can reach both the Kubernetes VIP and every Talos node API.
3. The reviewed OpenTofu plan changes only rendered machine-configuration data;
   it must not replace `talos_machine_secrets.homelab` or
   `talos_machine_bootstrap.homelab`.
4. Current and proposed machine configurations are stored as mode-0600 ignored
   files and validated with `talosctl validate`.
5. The Cilium OCI chart is cached and its signature and digest are verified.
6. The previous Talos machine configurations are retained as the rollback
   source.

## Cutover stages

1. Render and review the proposed Talos configurations.
2. Render the pinned Cilium chart locally and inspect cluster-scoped RBAC and
   host mounts.
3. Apply the proposed Talos configuration to one node with `--dry-run` and
   review the response.
4. During a maintenance window, deliver the reviewed Talos configuration to
   the three nodes. Expect Flannel and kube-proxy removal.
5. Immediately install Cilium from the cached, pinned OCI chart using the
   reviewed public values.
6. Wait for the Cilium DaemonSet and operator, recycle unmanaged CoreDNS pods,
   and verify that every non-host-network pod is Cilium-managed.
7. Run Cilium connectivity tests plus Kubernetes API, DNS, cross-node, service,
   and controlled node-reboot checks.
8. Commit the exact release as a Flux-managed component only after bootstrap;
   Flux must adopt identical values without changing the live Helm release.

Do not enable namespace default-deny policies during this operation.

## Rollback

If Cilium cannot establish healthy networking, keep Talos API access and the
Kubernetes API VIP open. Uninstall the partial Cilium Helm release, then restore
the retained pre-cutover machine configuration to each node. Wait for Talos to
recreate Flannel and kube-proxy and recycle non-host-network pods.

Rollback is complete only when all nodes are Ready, Flannel and kube-proxy have
three Ready pods each, CoreDNS resolves Kubernetes service names, and cross-node
pod traffic succeeds. Preserve command output and health evidence from both the
failed cutover and rollback.
