locals {
  inventory          = yamldecode(file(var.inventory_file)).homelab
  cluster_name       = local.inventory.name
  cluster_endpoint   = "https://${local.inventory.network.kubernetes_vip}:6443"
  talos_version      = local.inventory.talos.version
  kubernetes_version = "v1.37.0"
  installer_image    = "factory.talos.dev/metal-installer-secureboot/${local.inventory.talos.schematic}:${local.talos_version}"

  control_plane_nodes = {
    for name, node in local.inventory.nodes : name => {
      address       = node.intended_ip
      install_disk  = node.install_disk
      ethernet_link = node.ethernet_link
    }
  }
  node_addresses = [for node in local.control_plane_nodes : node.address]
}

# Retain this fresh identity across node enrollment, replacement and recovery.
# Cluster bootstrap lives at one separate stable address in cluster_bootstrap.tf.
resource "talos_machine_secrets" "homelab" {
  talos_version = local.talos_version

  lifecycle {
    prevent_destroy = true
  }
}

data "talos_machine_configuration" "controlplane" {
  for_each = local.control_plane_nodes

  cluster_name       = local.cluster_name
  cluster_endpoint   = local.cluster_endpoint
  machine_type       = "controlplane"
  machine_secrets    = talos_machine_secrets.homelab.machine_secrets
  talos_version      = local.talos_version
  kubernetes_version = local.kubernetes_version
  docs               = false
  examples           = false

  config_patches = [
    yamlencode({
      apiVersion = "v1alpha1"
      kind       = "Layer2VIPConfig"
      name       = local.inventory.network.kubernetes_vip
      link       = each.value.ethernet_link
    }),
    yamlencode({
      apiVersion = "v1alpha1"
      kind       = "UnattendedInstallConfig"
      reboot     = true
      installer = {
        image = local.installer_image
      }
      provisioning = {
        diskSelector = {
          match = "disk.dev_path == ${jsonencode(each.value.install_disk)}"
        }
        wipe = false
      }
    }),
    yamlencode({
      apiVersion = "v1alpha1"
      kind       = "KubeNodeConfig"
      taints = {
        "$patch" = "delete"
      }
    }),
    yamlencode({
      apiVersion = "v1alpha1"
      kind       = "HostnameConfig"
      hostname   = each.key
      auto = {
        "$patch" = "delete"
      }
    }),
    yamlencode({
      apiVersion  = "v1alpha1"
      kind        = "ResolverConfig"
      nameservers = local.inventory.network.dns
      searchDomains = {
        domains        = []
        disableDefault = true
      }
    }),
    # Cilium owns pod networking and service load-balancing. These documents
    # match the Talos v1.14 no-kube-proxy Cilium configuration.
    yamlencode({
      apiVersion = "v1alpha1"
      kind       = "KubeFlannelCNIConfig"
      "$patch"   = "delete"
    }),
    yamlencode({
      apiVersion = "v1alpha1"
      kind       = "KubeProxyConfig"
      enabled    = false
    }),
    yamlencode(local.github_actions_authentication_config),
  ]
  # Rendering has no node side effects. Delivery is a separate reviewed operation.
}

data "talos_client_configuration" "homelab" {
  cluster_name         = local.cluster_name
  client_configuration = talos_machine_secrets.homelab.client_configuration
  endpoints            = local.node_addresses
  nodes                = local.node_addresses
}
