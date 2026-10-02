# Raspberry Pi control runner

The Raspberry Pi 500 is the out-of-cluster execution host for privileged
OpenTofu plans and applies. It must be registered only with the private
`nunoferna/talos-homelab-gitops` repository. Public pull requests must never
schedule jobs on it.

The preparation playbook requires a 64-bit ARM kernel and userspace, then
installs checksum-pinned ARM64 builds of the GitHub Actions runner, OpenTofu and
kubectl. It does not register or start the runner and never handles a GitHub
registration token.

## Prepare the host

Set the operator-local SSH destination and run the playbook:

```sh
export PI_HOST=REPLACE_WITH_VERIFIED_ADDRESS
export PI_USER=REPLACE_WITH_OPERATOR_ACCOUNT

ansible-playbook \
  -i management/ansible/inventory.yaml \
  management/ansible/runner.yaml
```

Review the play recap before registering anything. The expected binaries are:

```sh
ssh "${PI_USER}@${PI_HOST}" \
  'tofu version && kubectl version --client && test -x /opt/actions-runner/current/config.sh'
```

## Register only with the private repository

In the private repository, open **Settings → Actions → Runners → New
self-hosted runner** and generate a short-lived registration token. On the Pi,
read it without placing it in shell history:

```sh
read -rsp 'Runner registration token: ' RUNNER_TOKEN
echo

sudo -u github-runner /opt/actions-runner/current/config.sh \
  --url https://github.com/nunoferna/talos-homelab-gitops \
  --token "${RUNNER_TOKEN}" \
  --name pi500-control \
  --labels homelab-control \
  --work /var/lib/github-runner/work \
  --unattended

unset RUNNER_TOKEN
cd /opt/actions-runner/current
sudo ./svc.sh install github-runner
sudo ./svc.sh start
sudo ./svc.sh status
```

Confirm that `pi500-control` is online in the private repository before
configuring deployment secrets. Do not add the runner to the public repository.

## Security boundary

- The runner receives jobs only from the private repository.
- The private workflow checks out only a protected, merged public commit.
- Cluster and R2 credentials are injected through GitHub environments.
- Runtime files are created as hidden files below the job workspace and removed
  after every job.
- Bootstrap credentials and the state passphrase remain recoverable without
  Kubernetes or OpenBao.

The control host must report `aarch64` from `uname -m` and `arm64` from
`dpkg --print-architecture`. The private workflow pins Node 24 action releases;
GitHub no longer supports JavaScript actions on Linux ARM32 runners.
