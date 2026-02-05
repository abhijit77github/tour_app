# MongoDB Persistent Volume
resource "kubernetes_persistent_volume" "mongodb_pv" {
  count = var.mongodb_replica_count == 1 ? 1 : 0
  
  metadata {
    name = "${var.app_name}-mongodb-pv"
  }

  spec {
    capacity = {
      storage = var.mongodb_storage_size
    }
    
    access_modes = ["ReadWriteOnce"]
    
    persistent_volume_reclaim_policy = "Retain"
    
    persistent_volume_source {
      host_path {
        path = "/mnt/data/mongodb"
      }
    }
  }
}

# MongoDB Persistent Volume Claim
resource "kubernetes_persistent_volume_claim" "mongodb_pvc" {
  metadata {
    name      = "${var.app_name}-mongodb-pvc"
    namespace = kubernetes_namespace.tour_app.metadata[0].name
    labels    = local.app_labels
  }

  spec {
    access_modes       = ["ReadWriteOnce"]
    storage_class_name = "standard"
    
    resources {
      requests = {
        storage = var.mongodb_storage_size
      }
    }
  }

  depends_on = [kubernetes_namespace.tour_app]
}

# MongoDB ConfigMap
resource "kubernetes_config_map" "mongodb_config" {
  metadata {
    name      = "${var.app_name}-mongodb-config"
    namespace = kubernetes_namespace.tour_app.metadata[0].name
    labels    = local.app_labels
  }

  data = {
    "init.js" = file("${path.module}/mongodb-init.js")
  }

  depends_on = [kubernetes_namespace.tour_app]
}

# MongoDB Service
resource "kubernetes_service" "mongodb" {
  metadata {
    name      = "mongodb"
    namespace = kubernetes_namespace.tour_app.metadata[0].name
    labels    = local.app_labels
  }

  spec {
    selector = {
      "app.kubernetes.io/name" = "mongodb"
    }

    port {
      port        = local.mongodb_port
      target_port = local.mongodb_port
      protocol    = "TCP"
      name        = "mongodb"
    }

    type = "ClusterIP"
  }

  depends_on = [kubernetes_namespace.tour_app]
}

# MongoDB Deployment
resource "kubernetes_deployment" "mongodb" {
  metadata {
    name      = "mongodb"
    namespace = kubernetes_namespace.tour_app.metadata[0].name
    labels = merge(
      local.app_labels,
      {
        "app.kubernetes.io/name" = "mongodb"
      }
    )
  }

  spec {
    replicas = var.mongodb_replica_count

    selector {
      match_labels = {
        "app.kubernetes.io/name" = "mongodb"
      }
    }

    template {
      metadata {
        labels = merge(
          local.app_labels,
          {
            "app.kubernetes.io/name" = "mongodb"
          }
        )
      }

      spec {
        container {
          image = "mongo:${var.mongodb_version}"
          name  = "mongodb"

          port {
            container_port = local.mongodb_port
            name           = "mongodb"
          }

          env {
            name  = "MONGO_INITDB_ROOT_USERNAME"
            value = "admin"
          }

          env {
            name = "MONGO_INITDB_ROOT_PASSWORD"
            value_from {
              secret_key_ref {
                name = kubernetes_secret.mongodb_credentials.metadata[0].name
                key  = "password"
              }
            }
          }

          resources {
            requests = {
              cpu    = "100m"
              memory = "256Mi"
            }
            limits = {
              cpu    = "500m"
              memory = "512Mi"
            }
          }

          volume_mount {
            name       = "mongodb-storage"
            mount_path = "/data/db"
          }

          volume_mount {
            name       = "mongodb-config"
            mount_path = "/docker-entrypoint-initdb.d"
          }

          liveness_probe {
            exec {
              command = [
                "mongosh",
                "--eval",
                "db.adminCommand('ping')"
              ]
            }
            initial_delay_seconds = 30
            period_seconds        = 10
          }

          readiness_probe {
            exec {
              command = [
                "mongosh",
                "--eval",
                "db.adminCommand('ping')"
              ]
            }
            initial_delay_seconds = 5
            period_seconds        = 5
          }
        }

        volume {
          name = "mongodb-storage"
          persistent_volume_claim {
            claim_name = kubernetes_persistent_volume_claim.mongodb_pvc.metadata[0].name
          }
        }

        volume {
          name = "mongodb-config"
          config_map {
            name = kubernetes_config_map.mongodb_config.metadata[0].name
          }
        }

        restart_policy = "Always"
      }
    }
  }

  depends_on = [
    kubernetes_namespace.tour_app,
    kubernetes_persistent_volume_claim.mongodb_pvc
  ]
}

# MongoDB Secret for credentials
resource "kubernetes_secret" "mongodb_credentials" {
  metadata {
    name      = "${var.app_name}-mongodb-credentials"
    namespace = kubernetes_namespace.tour_app.metadata[0].name
    labels    = local.app_labels
  }

  type = "Opaque"

  data = {
    username = base64encode("admin")
    password = base64encode(random_password.mongodb_password.result)
  }

  depends_on = [kubernetes_namespace.tour_app]
}

# Generate random password for MongoDB
resource "random_password" "mongodb_password" {
  length  = 32
  special = true
}
