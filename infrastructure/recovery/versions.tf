terraform {
  required_version = "= 1.12.6"

  required_providers {
    cloudflare = {
      source  = "cloudflare/cloudflare"
      version = "= 5.24.0"
    }
  }
}

# API credentials are injected as CLOUDFLARE_API_TOKEN, never as resources,
# tfvars, outputs or generated R2 object credentials in OpenTofu state.
provider "cloudflare" {}
