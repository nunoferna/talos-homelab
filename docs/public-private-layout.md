# Public and private repository boundary

Keep reusable code and reviewable platform resources separate from environment
identity, live reconciliation, and recovery material.

## Public foundation repository

Safe to publish after automated and manual review:

- OpenTofu and Ansible source code
- the OpenTofu-owned, day-zero Cilium Helm release
- dependency lock files and immutable public artifact digests
- documentation-only inventories using reserved addresses and example identifiers
- generic operating procedures with no environment history
- CI validation and secret scanning

## Public platform repository

The public platform repository is a reusable catalog above the CNI layer, not
the cluster's Flux entry point. It may contain:

- pinned Flux `HelmRepository`, `OCIRepository`, and `HelmRelease` resources
- generic storage, OpenBao, External Secrets Operator, ingress, and
  monitoring configuration
- namespaces, service accounts, RBAC, and network policies without private
  names, addresses, credentials, or provider account identifiers
- policy and schema validation that rejects plaintext Kubernetes `Secret`
  resources except explicitly documented test fixtures

Publishing Kubernetes YAML does not make it safe automatically. Treat internal
DNS names, IP ranges, certificate subjects, storage endpoints, tenant names,
and application metadata as private unless deliberately sanitized.

Cilium is excluded from Flux ownership. The foundation repository owns its
Helm release through a dedicated OpenTofu root and separate encrypted state.

## Private live repository

Access-controlled and backed up independently:

- real node names, addresses, MAC addresses, disk identifiers, and topology
- cluster-specific operational history and recovery notes
- the `clusters/homelab` Flux reconciliation root
- environment-specific values and references to reviewed public-platform
  revisions
- SOPS-encrypted Kubernetes secrets only for approved bootstrap exceptions
- `.sops.yaml` containing age *recipients* only

The private repository still must not contain plaintext Kubernetes secrets,
OpenTofu state or plans, Talos machine configurations, kubeconfigs, age private
keys, deploy-key private material, or decrypted etcd snapshots.

## Secret delivery boundary

OpenBao is the normal system of record for application secrets. Applications
consume narrowly scoped values through External Secrets Operator (ESO), using
Kubernetes authentication and one policy per namespace or trust boundary.

SOPS is an exception path for secrets that must exist before OpenBao and ESO are
available, or for a component that cannot use them. Keep those exceptions on an
explicit allowlist. Never commit OpenBao root tokens, unseal material, or
recovery keys, even as SOPS ciphertext.

ESO-created Kubernetes `Secret` objects are stored in Kubernetes etcd. Where a
workload must avoid that persistence, prefer an OpenBao Agent or CSI-based
delivery path instead of ESO synchronization.

## Recovery custody outside both repositories

Store these in independently controlled encrypted backup locations:

- age private recovery keys
- OpenBao unseal or recovery material and break-glass credentials
- the OpenTofu state-encryption passphrase
- encrypted etcd snapshots and their decryption material
- Talos and Kubernetes break-glass credentials
- Git hosting recovery codes and repository administration credentials

Compromise of Git history is permanent. Sanitize identifiers before the first
public push; deleting them in a later commit is insufficient.
