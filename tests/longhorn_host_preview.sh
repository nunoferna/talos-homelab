#!/bin/bash
# Synthetic safety tests; never contacts a cluster or reads real keys.
set -euo pipefail
umask 077
longhorn_fixture_dir="$(mktemp -d "${TMPDIR:-/tmp}/homelab-longhorn-preview-test.XXXXXX")"
export LONGHORN_PUBLIC_DIRECTORY="$PWD"
export LONGHORN_PRIVATE_VARS="$PWD/tests/fixtures/longhorn-host/targets.yaml"
export LONGHORN_TALOSCONFIG="$longhorn_fixture_dir/talosconfig"
export LONGHORN_KUBECONFIG="$longhorn_fixture_dir/kubeconfig"
export LONGHORN_FIXTURE_LOG="$longhorn_fixture_dir/previews.log"
export ANSIBLE_LOCAL_TEMP="$longhorn_fixture_dir/ansible"
export ANSIBLE_LOG_PATH=/dev/null
export PATH="$PWD/tests/fixtures/longhorn-host:$PATH"
printf 'NON_SECRET_FIXTURE\n' > "$LONGHORN_TALOSCONFIG"
printf 'NON_SECRET_FIXTURE\n' > "$LONGHORN_KUBECONFIG"
chmod 0600 "$LONGHORN_TALOSCONFIG" "$LONGHORN_KUBECONFIG"
playbook="$PWD/management/ansible/talos-longhorn-host-preview.yaml"
"${ANSIBLE_PLAYBOOK:-ansible-playbook}" "$playbook" > "$longhorn_fixture_dir/pass.log" 2>&1
test "$(wc -l < "$LONGHORN_FIXTURE_LOG" | tr -d ' ')" = 1
test "$(< "$LONGHORN_FIXTURE_LOG")" = 192.0.2.1
for guard in wrong-server wrong-uid wrong-client wrong-mode wrong-node-version \
  wrong-address not-ready wrong-kubelet failed-cilium failed-flux absent-flux stale-flux failed-health; do
  case "$guard" in
    wrong-server) export LONGHORN_FIXTURE_SERVER=https://192.0.2.71:6443 ;;
    wrong-uid) export LONGHORN_FIXTURE_UID=22222222-2222-2222-2222-222222222222 ;;
    wrong-client) export LONGHORN_FIXTURE_CLIENT=v1.13.0 ;;
    wrong-mode) chmod 0644 "$LONGHORN_TALOSCONFIG" ;;
    wrong-node-version) export LONGHORN_FIXTURE_NODE_VERSION=v1.14.2 ;;
    wrong-address) export LONGHORN_FIXTURE_NODE_ADDRESS=192.0.2.4 ;;
    not-ready) export LONGHORN_FIXTURE_NODE_READY=False ;;
    wrong-kubelet) export LONGHORN_FIXTURE_KUBELET=v1.36.0 ;;
    failed-cilium) export LONGHORN_FIXTURE_CILIUM=fail ;;
    failed-flux) export LONGHORN_FIXTURE_FLUX=False ;;
    absent-flux) export LONGHORN_FIXTURE_FLUX=absent ;;
    stale-flux) export LONGHORN_FIXTURE_FLUX_GENERATION=0 ;;
    failed-health) export LONGHORN_FIXTURE_HEALTH=fail ;;
  esac
  if "${ANSIBLE_PLAYBOOK:-ansible-playbook}" "$playbook" \
    > "$longhorn_fixture_dir/$guard.log" 2>&1; then
    printf 'Expected preview refusal: %s\n' "$guard" >&2
    exit 1
  fi
  test "$(wc -l < "$LONGHORN_FIXTURE_LOG" | tr -d ' ')" = 1
  unset LONGHORN_FIXTURE_SERVER LONGHORN_FIXTURE_UID LONGHORN_FIXTURE_CLIENT
  unset LONGHORN_FIXTURE_NODE_VERSION LONGHORN_FIXTURE_NODE_ADDRESS
  unset LONGHORN_FIXTURE_NODE_READY LONGHORN_FIXTURE_KUBELET LONGHORN_FIXTURE_HEALTH
  unset LONGHORN_FIXTURE_CILIUM LONGHORN_FIXTURE_FLUX LONGHORN_FIXTURE_FLUX_GENERATION
  chmod 0600 "$LONGHORN_TALOSCONFIG"
done
for invalid_contract in 'longhorn_host_target=unreviewed' 'longhorn_host_phase=apply' \
  'longhorn_disposable_poc_accepted=false'; do
  if "${ANSIBLE_PLAYBOOK:-ansible-playbook}" "$playbook" --extra-vars "$invalid_contract" \
    > "$longhorn_fixture_dir/contract.log" 2>&1; then
    echo 'Unreviewed target/phase/acceptance unexpectedly passed.' >&2
    exit 1
  fi
  test "$(wc -l < "$LONGHORN_FIXTURE_LOG" | tr -d ' ')" = 1
done
export LONGHORN_FIXTURE_PREVIEW=fail
if "${ANSIBLE_PLAYBOOK:-ansible-playbook}" "$playbook" > "$longhorn_fixture_dir/failed-preview.log" 2>&1; then
  echo 'A failed native preview unexpectedly passed.' >&2
  exit 1
fi
if grep -q NON_SECRET_SYNTHETIC_MACHINE_DIFF "$longhorn_fixture_dir/"*.log; then
  echo 'Machine preview output was not suppressed.' >&2
  exit 1
fi
printf 'PASS: single-node preview; 16 refusal guards; failed native output suppressed.\n'
# Retain non-secret diagnostic fixtures only, as for backup preview tests.
