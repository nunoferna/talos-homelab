output "machine_configurations" {
  description = "Disposable configurations keyed by inventory node name. Contains private cluster material; export only to protected local files."
  value       = { for name, config in data.talos_machine_configuration.controlplane : name => config.machine_configuration }
  sensitive   = true
}

output "talosconfig" {
  description = "Cluster operator credentials with all control-plane endpoints and nodes. Use an explicit node target for node operations; export only to a protected local file."
  value       = data.talos_client_configuration.homelab.talos_config
  sensitive   = true
}
