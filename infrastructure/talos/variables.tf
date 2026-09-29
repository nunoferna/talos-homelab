variable "state_passphrase" {
  description = "Independently backed-up encryption secret, supplied locally at runtime. Never store it in Git, tfvars, or backend configuration."
  type        = string
  nullable    = false
  sensitive   = true
  ephemeral   = true

  validation {
    condition     = length(var.state_passphrase) >= 32
    error_message = "Use a securely generated encryption secret of at least 32 characters."
  }
}

variable "inventory_file" {
  description = "Path to the private environment inventory. Use an ignored file outside the public Git history."
  type        = string
  nullable    = false

  validation {
    condition = (
      length(trimspace(var.inventory_file)) > 0 &&
      can(yamldecode(file(var.inventory_file)).homelab)
    )
    error_message = "Supply a readable private YAML file containing a top-level homelab object."
  }
}

variable "bootstrap_endpoint" {
  description = "Explicit transport endpoint for the one-time cluster bootstrap; never use the Kubernetes VIP."
  type        = string
  nullable    = false

  validation {
    condition = can(regex(
      "^(127\\.0\\.0\\.1:[0-9]{1,5}|([0-9]{1,3}\\.){3}[0-9]{1,3}(:[0-9]{1,5})?)$",
      var.bootstrap_endpoint,
    ))
    error_message = "Use an explicit IPv4 node endpoint or a verified localhost tunnel endpoint."
  }
}
