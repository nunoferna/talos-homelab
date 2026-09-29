# Consume a single authenticated `talosctl get securitystate -o json` result
# using jq -s -e -f. Boot medium and chassis identity must be verified separately.
length == 1 and
(.[0] |
  .metadata.type == "SecurityStates.talos.dev" and
  .metadata.id == "securitystate" and
  .spec.secureBoot == true and
  .spec.bootedWithUKI == true and
  .spec.moduleSignatureEnforced == true)
