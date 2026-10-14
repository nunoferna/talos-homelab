# Test fixture only. No list, wildcard, write, token, or admin capability.
path "kv/data/poc/eso-demo" {
  capabilities = ["read"]
}
