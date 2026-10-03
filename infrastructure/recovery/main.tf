locals {
  snapshot_prefix = "etcd/"
  # Planning headroom, NOT an upper bound on Cloudflare lifecycle deletion lag.
  expiry_headroom_days = 2
  projected_storage_bytes = ceil(
    var.snapshot_size_bound_bytes * var.snapshots_per_day *
    (var.retention_days + local.expiry_headroom_days) * 1.25
  )
}

resource "cloudflare_r2_bucket" "snapshots" {
  account_id    = var.account_id
  name          = var.bucket_name
  jurisdiction  = var.jurisdiction
  storage_class = "Standard"

  lifecycle {
    prevent_destroy = true

    precondition {
      condition     = local.projected_storage_bytes <= var.storage_budget_bytes
      error_message = "Snapshot frequency, size bound and retention exceed the reserved recovery storage budget."
    }

    precondition {
      condition     = var.storage_budget_bytes + var.other_account_storage_bytes <= 8000000000
      error_message = "Recovery plus other R2 usage must fit an 8 GB planning ceiling, leaving free-tier headroom."
    }
  }
}

resource "cloudflare_r2_managed_domain" "snapshots" {
  account_id   = var.account_id
  bucket_name  = cloudflare_r2_bucket.snapshots.name
  jurisdiction = var.jurisdiction
  enabled      = false

  lifecycle {
    prevent_destroy = true
  }
}

resource "cloudflare_r2_bucket_lock" "snapshots" {
  account_id   = var.account_id
  bucket_name  = cloudflare_r2_bucket.snapshots.name
  jurisdiction = var.jurisdiction
  rules = [{
    id      = "etcd-retention"
    enabled = true
    prefix  = local.snapshot_prefix
    condition = {
      type            = "Age"
      max_age_seconds = var.lock_days * 86400
    }
  }]

  lifecycle {
    prevent_destroy = true
  }
}

resource "cloudflare_r2_bucket_lifecycle" "snapshots" {
  account_id   = var.account_id
  bucket_name  = cloudflare_r2_bucket.snapshots.name
  jurisdiction = var.jurisdiction
  rules = [{
    id         = "etcd-expiry"
    enabled    = true
    conditions = { prefix = local.snapshot_prefix }
    delete_objects_transition = {
      condition = {
        type    = "Age"
        max_age = var.retention_days * 86400
      }
    }
    abort_multipart_uploads_transition = {
      condition = {
        type    = "Age"
        max_age = 86400
      }
    }
  }]

  lifecycle {
    prevent_destroy = true
  }
}
