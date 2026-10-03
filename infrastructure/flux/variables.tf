variable "state_passphrase" {
  description = "Independently backed-up encryption secret supplied only at runtime."
  type        = string
  nullable    = false
  sensitive   = true
  ephemeral   = true

  validation {
    condition     = length(var.state_passphrase) >= 32
    error_message = "Use a securely generated encryption secret of at least 32 characters."
  }
}

variable "kubeconfig_file" {
  description = "Path to the protected, short-lived kubeconfig used by the Helm provider."
  type        = string
  nullable    = false

  validation {
    condition     = length(trimspace(var.kubeconfig_file)) > 0 && can(file(var.kubeconfig_file))
    error_message = "Supply the path to a readable kubeconfig file."
  }
}
