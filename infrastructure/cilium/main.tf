locals {
  release     = yamldecode(file("${path.module}/release.yaml"))
  values_file = "${path.module}/values.yaml"
}

provider "helm" {
  kubernetes = {
    config_path = var.kubeconfig_file
  }
}

resource "helm_release" "cilium" {
  name       = "cilium"
  namespace  = "kube-system"
  repository = local.release.repository
  chart      = local.release.chart
  version    = local.release.version

  values = [file(local.values_file)]

  timeout = 600
  wait    = true

  lifecycle {
    precondition {
      condition     = filesha256(local.values_file) == local.release.valuesSha256
      error_message = "values.yaml does not match the reviewed checksum in release.yaml."
    }
  }
}
