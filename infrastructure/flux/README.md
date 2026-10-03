# Flux bootstrap OpenTofu root

This root owns only the day-zero Flux Operator and `FluxInstance`. It uses a
separate encrypted R2 state key from Cilium and runs through the private
reviewed-plan workflow. No operator should install Flux with `kubectl apply` or
`flux bootstrap`.

The pinned Flux instance reads this public repository over HTTPS and reconciles
`clusters/homelab`. Public repositories need no deploy key; adding one would
create a credential without adding confidentiality or authorization.

The Helm provider uses ConfigMaps for release metadata so the plan identity can
refresh this non-secret state without permission to read every Secret in
`flux-system`. Neither chart values file may contain credentials.

## Ownership boundary

- OpenTofu owns the `flux-operator` and `flux-instance` Helm releases.
- Flux Operator owns the Flux controllers and generated sync objects.
- Flux controllers own resources reachable from `clusters/homelab`.
- Cilium remains exclusively owned by its separate OpenTofu root.

Do not declare the same Kubernetes object in more than one layer.

## Rollback

Prefer a Git revert and a reviewed saved plan. Removing this root plans removal
of Flux and stops Git reconciliation; it does not delete workloads previously
created by Flux. Review every planned deletion and preserve the last encrypted
state object version before any teardown.
