# Cilium OpenTofu root

This root permanently owns the cluster's Cilium Helm release. Cilium is below
Flux in the dependency graph and must never be managed by both OpenTofu and
Flux.

It uses a separate encrypted and locked R2 state at
`homelab/cilium.tfstate`, isolating CNI lifecycle and blast radius from the
Talos identity and bootstrap state.

## Runtime inputs

- `kubeconfig_file`: protected local operator kubeconfig used by the Helm
  provider; never committed or stored in state.
- `state_passphrase`: ephemeral encryption input shared with the existing
  state-custody procedure.
- backend bucket, endpoint, and credentials: supplied through the ignored
  backend file and scoped AWS profile.

## Safe workflow

```sh
export TF_VAR_kubeconfig_file=/absolute/path/to/protected/kubeconfig
export TF_VAR_state_passphrase=REPLACE_FROM_PROTECTED_RUNTIME_SOURCE
export AWS_PROFILE=REPLACE_WITH_SCOPED_R2_PROFILE

tofu -chdir=infrastructure/cilium init \
  -backend-config=/absolute/path/to/private/backend.r2.hcl
tofu -chdir=infrastructure/cilium fmt -check -diff
tofu -chdir=infrastructure/cilium validate
tofu -chdir=infrastructure/cilium plan \
  -out=/absolute/path/to/private/reviewed.tfplan
```

Apply only the reviewed saved plan. The existing day-zero release at
`kube-system/cilium` was adopted through a declarative import recorded in Git
history. Ordinary plans must not replace or delete it.

The values checksum in `release.yaml` prevents an unreviewed values-file edit
from reaching Helm. When intentionally changing values, review the rendered
chart and update the checksum in the same commit.
