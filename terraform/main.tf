terraform {
  required_version = ">= 1.0"
  required_providers {
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.23"
    }
    helm = {
      source  = "hashicorp/helm"
      version = "~> 2.11"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
  }
}

variable "kubeconfig_path" {
  description = "Path to the kubeconfig file"
  type        = string
  default     = "~/.kube/config"
}

provider "kubernetes" {
  config_path = try(var.kubeconfig_path, "~/.kube/config")
  
  # Alternatively, for cloud providers:
  # For AWS EKS:
  # host                   = aws_eks_cluster.main.endpoint
  # cluster_ca_certificate = base64decode(aws_eks_cluster.main.certificate_authority[0].data)
  # token                  = data.aws_eks_auth.main.token
  
  # For GCP GKE:
  # host                   = "https://${google_container_cluster.main.endpoint}"
  # cluster_ca_certificate = base64decode(google_container_cluster.main.master_auth[0].cluster_ca_certificate)
  # token                  = data.google_client_config.default.access_token
  
  # For Azure AKS:
  # host                   = azurerm_kubernetes_cluster.main.kube_config[0].host
  # cluster_ca_certificate = base64decode(azurerm_kubernetes_cluster.main.kube_config[0].cluster_ca_certificate)
  # client_certificate     = base64decode(azurerm_kubernetes_cluster.main.kube_config[0].client_certificate)
  # client_key             = base64decode(azurerm_kubernetes_cluster.main.kube_config[0].client_key)
}

provider "helm" {
  kubernetes {
    config_path = try(var.kubeconfig_path, "~/.kube/config")
  }
}

# Create namespace
resource "kubernetes_namespace" "tour_app" {
  metadata {
    name = var.kubernetes_namespace
    labels = {
      "app.kubernetes.io/name"       = var.app_name
      "app.kubernetes.io/environment" = var.environment
    }
  }
}

# Local values
locals {
  app_labels = {
    "app.kubernetes.io/name"       = var.app_name
    "app.kubernetes.io/environment" = var.environment
    "managed-by"                    = "terraform"
  }
  
  mongodb_host = "mongodb"
  mongodb_port = 27017
  frontend_origin = var.frontend_url_override != "" ? var.frontend_url_override : "http://${var.domain_name}"
}
