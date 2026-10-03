variable "state_passphrase" {
  description = "Independently backed-up state/plan encryption secret, supplied only at runtime."
  type        = string
  sensitive   = true
  nullable    = false

  validation {
    condition     = length(var.state_passphrase) >= 32
    error_message = "The state encryption passphrase must have at least 32 characters."
  }
}

variable "account_id" {
  description = "Private Cloudflare account identifier supplied by the control repository."
  type        = string
  sensitive   = true
  nullable    = false

  validation {
    condition     = can(regex("^[0-9a-f]{32}$", var.account_id))
    error_message = "Supply the Cloudflare account's 32-character hexadecimal identifier."
  }
}

variable "bucket_name" {
  description = "New dedicated snapshot bucket; never the existing OpenTofu state bucket."
  type        = string
  sensitive   = true
  nullable    = false

  validation {
    condition     = can(regex("^[a-z0-9][a-z0-9-]{1,61}[a-z0-9]$", var.bucket_name))
    error_message = "Use a 3-63 character lower-case bucket name with letters, digits and internal hyphens."
  }

  validation {
    condition     = var.bucket_name != var.state_bucket_name
    error_message = "Snapshot and state buckets must be different."
  }
}

variable "state_bucket_name" {
  description = "Protected runtime backend bucket name, used only to reject accidental targeting."
  type        = string
  sensitive   = true
  nullable    = false

  validation {
    condition     = length(trimspace(var.state_bucket_name)) > 0
    error_message = "Supply the actual backend bucket name."
  }
}

variable "jurisdiction" {
  description = "Snapshot storage jurisdiction; changing it requires a separately reviewed migration."
  type        = string
  default     = "eu"
  nullable    = false

  validation {
    condition     = contains(["default", "eu"], var.jurisdiction)
    error_message = "This free-tier-oriented root supports default or EU jurisdiction only."
  }
}

variable "retention_days" {
  description = "Ciphertext expiry age. Keep the last verified recovery point independently before expiry."
  type        = number
  default     = 7
  nullable    = false

  validation {
    condition     = var.retention_days >= 2 && var.retention_days <= 30 && floor(var.retention_days) == var.retention_days
    error_message = "Choose an integer retention period between 2 and 30 days."
  }
}

variable "lock_days" {
  description = "Snapshot-prefix deletion/overwrite protection age; administrator-removable, not compliance WORM."
  type        = number
  default     = 7
  nullable    = false

  validation {
    condition     = var.lock_days >= 1 && var.lock_days <= var.retention_days && floor(var.lock_days) == var.lock_days
    error_message = "Choose an integer lock age of at least one day, no longer than retention."
  }
}

variable "snapshot_size_bound_bytes" {
  description = "Reviewed conservative upper bound for one compressed/encrypted snapshot, not a guessed default."
  type        = number
  nullable    = false

  validation {
    condition     = var.snapshot_size_bound_bytes > 0 && floor(var.snapshot_size_bound_bytes) == var.snapshot_size_bound_bytes
    error_message = "Supply a positive integer byte-size bound backed by sizing evidence."
  }
}

variable "snapshots_per_day" {
  description = "Must match the reviewed CronJob frequency; the staged 15-minute schedule is 96/day."
  type        = number
  default     = 96
  nullable    = false

  validation {
    condition     = var.snapshots_per_day >= 1 && var.snapshots_per_day <= 96 && floor(var.snapshots_per_day) == var.snapshots_per_day
    error_message = "Choose an integer number of snapshots/day between 1 and 96."
  }
}

variable "storage_budget_bytes" {
  description = "Account storage budget reserved for this snapshot prefix; no provider-side spending cap is implied."
  type        = number
  default     = 4000000000
  nullable    = false

  validation {
    condition     = var.storage_budget_bytes > 0 && var.storage_budget_bytes <= 8000000000
    error_message = "Reserve a positive recovery budget no larger than 8 decimal GB."
  }
}

variable "other_account_storage_bytes" {
  description = "Reviewed conservative bound for all other account R2 storage, including state and any other buckets."
  type        = number
  nullable    = false

  validation {
    condition     = var.other_account_storage_bytes >= 0
    error_message = "Supply a nonnegative bound for other account storage."
  }
}
