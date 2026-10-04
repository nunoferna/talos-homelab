output "bucket_name" {
  description = "Private destination name, consumed by private GitOps inputs only."
  value       = cloudflare_r2_bucket.snapshots.name
  sensitive   = true
}

output "s3_endpoint" {
  description = "Private jurisdiction-aware S3 endpoint; also used by the exact Cilium egress patch."
  value       = "https://${var.account_id}${var.jurisdiction == "eu" ? ".eu" : ""}.r2.cloudflarestorage.com"
  sensitive   = true
}

output "projected_storage_bytes" {
  description = "Mode-aware planning estimate with 25% headroom; PoC allows two objects, scheduled mode adds two expiry days. Not a billing cap."
  value       = local.projected_storage_bytes
}

output "backup_mode" {
  description = "Planning mode only; no Job or CronJob is activated by OpenTofu."
  value       = var.backup_mode
}
