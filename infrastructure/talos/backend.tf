terraform {
  # bucket and endpoints.s3 come from the reviewed local backend configuration.
  # Credentials come from a dedicated AWS CLI profile, never this file.
  backend "s3" {
    key                         = "homelab/talos.tfstate"
    region                      = "auto"
    use_lockfile                = true
    use_path_style              = true
    skip_credentials_validation = true
    skip_requesting_account_id  = true
    skip_region_validation      = true
    skip_metadata_api_check     = true
    skip_s3_checksum            = true
    # R2 does not implement S3's SSE request headers. OpenTofu's enforced
    # encryption below protects state before upload; R2 also encrypts at rest.
    encrypt = false
  }

  encryption {
    key_provider "pbkdf2" "state" {
      passphrase = var.state_passphrase
    }
    method "aes_gcm" "state" {
      keys = key_provider.pbkdf2.state
    }
    state {
      method   = method.aes_gcm.state
      enforced = true
    }
    plan {
      method   = method.aes_gcm.state
      enforced = true
    }
  }
}
