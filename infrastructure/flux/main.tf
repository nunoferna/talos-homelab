locals {
  releases             = yamldecode(file("${path.module}/releases.yaml"))
  operator_values_file = "${path.module}/operator-values.yaml"
  instance_values_file = "${path.module}/instance-values.yaml"
}

provider "helm" {
  helm_driver = "configmap"

  kubernetes = {
    config_path = var.kubeconfig_file
  }
}

resource "helm_release" "flux_operator" {
  name             = "flux-operator"
  namespace        = "flux-system"
  create_namespace = true
  repository       = local.releases.repository
  chart            = local.releases.operator.chart
  version          = local.releases.operator.version

  values = [file(local.operator_values_file)]

  atomic          = true
  cleanup_on_fail = true
  timeout         = 600
  wait            = true
  wait_for_jobs   = true

  lifecycle {
    precondition {
      condition     = filesha256(local.operator_values_file) == local.releases.operator.valuesSha256
      error_message = "operator-values.yaml does not match its reviewed checksum."
    }
  }
}

resource "helm_release" "flux_instance" {
  name       = "flux-instance"
  namespace  = "flux-system"
  repository = local.releases.repository
  chart      = local.releases.instance.chart
  version    = local.releases.instance.version

  values = [file(local.instance_values_file)]

  atomic          = true
  cleanup_on_fail = true
  timeout         = 600
  wait            = true
  wait_for_jobs   = true

  depends_on = [helm_release.flux_operator]

  lifecycle {
    precondition {
      condition     = filesha256(local.instance_values_file) == local.releases.instance.valuesSha256
      error_message = "instance-values.yaml does not match its reviewed checksum."
    }
  }
}
