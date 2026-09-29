# Cluster-level operation, kept at one stable address for this cluster identity.
# Never place bootstrap in a per-node loop or use it during node replacement.
# If state is lost after a successful RPC, restore/import this record after
# checking live etcd membership; do not blindly retry a fresh bootstrap apply.
locals {
  # Seed for the cluster-level bootstrap; all nodes share one configuration.
  bootstrap_node = "cp03"
}

resource "talos_machine_bootstrap" "homelab" {
  node                 = local.control_plane_nodes[local.bootstrap_node].address
  endpoint             = var.bootstrap_endpoint
  client_configuration = talos_machine_secrets.homelab.client_configuration

  timeouts = {
    create = "2m"
  }

  lifecycle {
    prevent_destroy = true
  }
}
