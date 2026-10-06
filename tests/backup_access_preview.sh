#!/bin/bash
# Synthetic metadata/client tests only; never reads production credential files.
set -euo pipefail
umask 077
backup_fixture_dir="$(mktemp -d "${TMPDIR:-/tmp}/homelab-backup-preview-test.XXXXXX")"
export BACKUP_PUBLIC_DIRECTORY="$PWD"
export BACKUP_ACCESS_PRIVATE_VARS="$PWD/tests/fixtures/backup-access/targets.yaml"
export BACKUP_ACCESS_TALOSCONFIG="$backup_fixture_dir/talosconfig"
export BACKUP_ACCESS_KUBECONFIG="$backup_fixture_dir/kubeconfig"
export BACKUP_FIXTURE_LOG="$backup_fixture_dir/previews.log"
export ANSIBLE_LOCAL_TEMP="$backup_fixture_dir/ansible"
export ANSIBLE_LOG_PATH=/dev/null
export PATH="$PWD/tests/fixtures/backup-access:$PATH"
printf 'NON_SECRET_FIXTURE_NOT_A_CERTIFICATE\n' > "$BACKUP_ACCESS_TALOSCONFIG"
printf 'NON_SECRET_FIXTURE_NOT_A_KUBECONFIG\n' > "$BACKUP_ACCESS_KUBECONFIG"
chmod 0600 "$BACKUP_ACCESS_TALOSCONFIG" "$BACKUP_ACCESS_KUBECONFIG"
preview_playbook="$PWD/management/ansible/talos-backup-access-preview.yaml"
"${ANSIBLE_PLAYBOOK:-ansible-playbook}" "$preview_playbook" > "$backup_fixture_dir/pass.log" 2>&1
test "$(wc -l < "$BACKUP_FIXTURE_LOG" | tr -d ' ')" = 3
if grep -q NON_SECRET_SYNTHETIC_PREVIEW "$backup_fixture_dir/pass.log"; then
  echo 'Sensitive preview output was not suppressed.' >&2
  exit 1
fi
for guard in wrong-server wrong-uid wrong-version wrong-mode; do
  case "$guard" in
    wrong-server) export BACKUP_FIXTURE_SERVER=https://192.0.2.71:6443 ;;
    wrong-uid) export BACKUP_FIXTURE_UID=22222222-2222-2222-2222-222222222222 ;;
    wrong-version) export BACKUP_FIXTURE_VERSION=v1.13.0 ;;
    wrong-mode) chmod 0644 "$BACKUP_ACCESS_TALOSCONFIG" ;;
  esac
  if "${ANSIBLE_PLAYBOOK:-ansible-playbook}" "$preview_playbook" \
    > "$backup_fixture_dir/$guard.log" 2>&1; then
    printf 'Expected preview refusal: %s\n' "$guard" >&2
    exit 1
  fi
  test "$(wc -l < "$BACKUP_FIXTURE_LOG" | tr -d ' ')" = 3
  unset BACKUP_FIXTURE_SERVER BACKUP_FIXTURE_UID BACKUP_FIXTURE_VERSION
  chmod 0600 "$BACKUP_ACCESS_TALOSCONFIG"
done
printf 'PASS: three dry-run previews; wrong cluster/client/mode refused; output suppressed.\n'
# Retain this small non-secret test directory for diagnostics; no key cleanup.
