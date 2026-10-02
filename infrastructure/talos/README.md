# Talos OpenTofu root

This root renders Talos control-plane configurations from a private inventory,
retains one cluster identity, and records one explicit cluster bootstrap. It
requires OpenTofu 1.12.6 because state and plan encryption are enforced.

## Inputs

- `inventory_file`: required path to a readable private YAML inventory. The
  committed `inventory/homelab.example.yaml` is documentation only.
- `bootstrap_endpoint`: required node or verified localhost tunnel endpoint for
  the one-time bootstrap resource. Never use the Kubernetes VIP.
- `state_passphrase`: required ephemeral encryption passphrase of at least 32
  characters. Back it up independently and never commit it.

Relative inventory paths are resolved from the process working directory. An
absolute path is clearer for operator and CI usage.

## Identity and state safety

`talos_machine_secrets.homelab` and `talos_machine_bootstrap.homelab` both use
`prevent_destroy`. Node configurations use stable, name-based `for_each` keys,
so inventory ordering does not change resource identities.

The S3-compatible backend is partially configured. Supply the private R2 bucket,
endpoint, and scoped credential profile through an ignored backend file and the
environment. OpenTofu encrypts state and saved plans before upload; the R2 bucket
must remain private with versioning/retention configured independently.

Never use `tofu state pull` as an encrypted backup: it emits decrypted state.
Preserve verified encrypted backend object versions and the independent
encryption key instead.

## GitHub Actions workload identity

Control-plane configurations include a Talos `KubeAuthenticationConfig` that
enables Kubernetes structured authentication for GitHub Actions. The trust is
restricted to the private `nunoferna/talos-homelab-gitops` repository ID, its
`cilium-deploy.yaml` workflow on `main`, manual dispatch events, and the
`cilium-plan` or `cilium-production` GitHub environment. The intended audience
is `talos-homelab-kubernetes`.

This configuration removes the need to store a Kubernetes client certificate
or long-lived bearer token in GitHub. It does not grant permissions by itself;
the separately reviewed RBAC manifest under `infrastructure/cilium` maps the two
environment-specific usernames to their required privileges.

Roll out authentication changes one control-plane node at a time. For each
node, validate the rendered machine configuration with Talos 1.14.1, inspect an
`apply-config --dry-run`, use Talos try mode, confirm API-server and etcd health,
then commit the configuration before moving to the next node. Keep the existing
administrator Talos and Kubernetes credentials available throughout.

To roll back, apply a previously reviewed rendered machine configuration that
does not contain the `KubeAuthenticationConfig`, again one node at a time. The
administrator client-certificate authentication path remains independent of
GitHub OIDC. Disable the GitHub workflow before removing its RBAC bindings.

## Safe workflow

```sh
export TF_VAR_inventory_file=/absolute/path/to/private/inventory.yaml
export TF_VAR_bootstrap_endpoint=REPLACE_WITH_VERIFIED_ENDPOINT
export TF_VAR_state_passphrase=REPLACE_FROM_PROTECTED_RUNTIME_SOURCE
export AWS_PROFILE=REPLACE_WITH_SCOPED_R2_PROFILE

tofu -chdir=infrastructure/talos init \
  -backend-config=/absolute/path/to/private/backend.r2.hcl
tofu -chdir=infrastructure/talos fmt -check -diff
tofu -chdir=infrastructure/talos validate
tofu -chdir=infrastructure/talos plan -out=/absolute/path/to/private/reviewed.tfplan
```

Review the complete plan for identity replacement, bootstrap replacement, and
node configuration changes. Applying rendered output changes does not deliver
configuration to nodes; delivery remains a separate reviewed operation.

The rendered configuration removes Talos' built-in Flannel deployment and
disables kube-proxy so Cilium can own pod networking and service routing. Never
deliver that configuration until the matching, pinned Cilium chart is locally
available and the CNI cutover runbook has been reviewed. Removing Flannel before
Cilium is ready causes an expected pod-network outage.

Export sensitive outputs only to mode-0600 files in ignored storage. Validate
rendered machine configurations with the matching `talosctl` release before any
node operation.
