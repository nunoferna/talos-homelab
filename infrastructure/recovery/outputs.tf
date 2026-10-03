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
  description = "Conservative planning estimate including 25% growth and two days of expiry headroom; not a billing cap."
  value       = local.projected_storage_bytes
}
