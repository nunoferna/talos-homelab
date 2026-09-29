# Public and private repository boundary

Keep reusable code separate from environment identity and recovery material.

## Public foundation repository

Safe to publish after automated and manual review:

- OpenTofu and Ansible source code
- dependency lock files and immutable public artifact digests
- documentation-only inventories using reserved addresses and example identifiers
- generic operating procedures with no environment history
- CI validation and secret scanning

## Private GitOps repository

Access-controlled and backed up independently:

- real node names, addresses, MAC addresses, disk identifiers, and topology
- cluster-specific operational history and recovery notes
- `clusters/homelab` Flux manifests
- SOPS-encrypted Kubernetes secrets
- `.sops.yaml` containing age *recipients* only

The private repository still must not contain plaintext Kubernetes secrets,
OpenTofu state or plans, Talos machine configurations, kubeconfigs, age private
keys, deploy-key private material, or decrypted etcd snapshots.

## Recovery custody outside both repositories

Store these in independently controlled encrypted backup locations:

- age private recovery keys
- the OpenTofu state-encryption passphrase
- encrypted etcd snapshots and their decryption material
- Talos and Kubernetes break-glass credentials
- Git hosting recovery codes and repository administration credentials

Compromise of Git history is permanent. Sanitize identifiers before the first
public push; deleting them in a later commit is insufficient.
