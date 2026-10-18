locals {
  release     = yamldecode(file("${path.module}/release.yaml"))
  values_file = "${path.module}/values.yaml"
  gateway_values = var.enable_gateway_api ? [yamlencode({
    rollOutCiliumPods = true
    operator          = { rollOutPods = true }
    updateStrategy = {
      type          = "RollingUpdate"
      rollingUpdate = { maxUnavailable = 1 }
    }
    gatewayAPI = {
      enabled               = true
      gatewayClass          = { create = true }
      externalTrafficPolicy = "Cluster"
    }
    l2announcements = { enabled = true }
  })] : []
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

  values = concat([file(local.values_file)], local.gateway_values)

  timeout = 600
  wait    = true

  lifecycle {
    precondition {
      condition     = filesha256(local.values_file) == local.release.valuesSha256
      error_message = "values.yaml does not match the reviewed checksum in release.yaml."
    }
  }
}
