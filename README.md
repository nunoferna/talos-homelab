# Talos homelab foundation

Reusable OpenTofu and Ansible building blocks for a three-node Talos Linux
cluster with Secure Boot, an API virtual IP, encrypted remote state, and a
separate provisioning host. OpenTofu also owns the day-zero Cilium Helm
release; Flux is intended to own Kubernetes workloads above the CNI layer.

This public repository contains code and documentation examples only. Generic
GitOps resources belong in a separate public platform repository. Real network
addresses, hardware identifiers, operational history, credentials, state,
recovery artifacts, and the live Flux reconciliation root belong in a private
repository or ignored local storage.

## Repository boundary

- `infrastructure/talos/`: OpenTofu configuration for Talos identity, machine
  configuration rendering, and the one-time cluster bootstrap record.
- `infrastructure/cilium/`: OpenTofu configuration for the Cilium Helm release,
  with an independent encrypted and locked state.
- `management/ansible/`: narrowly scoped provisioning-host discovery and
  single-node PXE staging tools.
- `inventory/homelab.example.yaml`: documentation-only inventory using the
  RFC 5737 TEST-NET-1 range and locally administered example MAC addresses.
- `docs/public-private-layout.md`: the required separation between public
  foundation code, public platform resources, private live data, and recovery
  material.
- `docs/platform-bootstrap-order.md`: the dependency-ordered path from Cilium
  through Flux, storage, OpenBao, External Secrets Operator, and applications.

Never apply the example inventory. Copy it into private storage, replace every
value, and pass its path explicitly at runtime.

## Validation

The repository pins OpenTofu 1.12.6, the Sidero Labs Talos provider 0.12.0, and
the HashiCorp Helm provider 3.3.0. Static CI checks scan for committed secrets
and validate YAML, Ansible, Python, and both OpenTofu roots.

Run the local checks from the repository root:

```sh
yamllint .
task validate
tofu fmt -check -diff -recursive infrastructure
```

OpenTofu validation requires provider initialization but does not require access
to the live backend:

```sh
tofu -chdir=infrastructure/talos init -backend=false
tofu -chdir=infrastructure/talos validate
tofu -chdir=infrastructure/cilium init -backend=false
tofu -chdir=infrastructure/cilium validate
```

## Private inputs

For a real plan, provide all environment-specific values explicitly. Example:

```sh
export GITOPS_REPO="${GITOPS_REPO:-$PWD/../talos-homelab-gitops}"
export TF_VAR_inventory_file="$GITOPS_REPO/inventory/homelab.yaml"
export TF_VAR_bootstrap_endpoint="REPLACE_WITH_VERIFIED_NODE_OR_TUNNEL_ENDPOINT"
export TF_VAR_state_passphrase="$(security find-generic-password -w -s homelab-state-passphrase)"
export AWS_PROFILE=REPLACE_WITH_SCOPED_R2_PROFILE

tofu -chdir=infrastructure/talos plan -out="$PWD/.local/reviewed.tfplan"
```

Review the saved plan before any apply. Pay particular attention to
`talos_machine_secrets.homelab` and `talos_machine_bootstrap.homelab`; both are
protected with `prevent_destroy` because replacing cluster identity is a
high-impact operation.

Generated Talos machine configurations, kubeconfigs, state files, plan files,
packet captures, age private keys, and etcd snapshots must never enter this
repository.

## Private deployment runner

The Raspberry Pi can host the out-of-cluster GitHub Actions runner used by the
private control repository. The public preparation playbook installs only
checksum-pinned tooling; registration remains a deliberate manual boundary. See
[the runner runbook](docs/rpi-actions-runner.md).
