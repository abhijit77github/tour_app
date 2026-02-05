# Backend ConfigMap
resource "kubernetes_config_map" "backend_config" {
  metadata {
    name      = "${var.app_name}-backend-config"
    namespace = kubernetes_namespace.tour_app.metadata[0].name
    labels    = local.app_labels
  }

  data = {
    "PORT"           = tostring(var.backend_port)
    "MONGODB_HOST"   = local.mongodb_host
    "MONGODB_PORT"   = tostring(local.mongodb_port)
    "MONGODB_DB"     = "tour_app"
    "JWT_SECRET"     = random_password.jwt_secret.result
    "ENVIRONMENT"    = var.environment
  }

  depends_on = [kubernetes_namespace.tour_app]
}

# Backend Secret
resource "kubernetes_secret" "backend_secrets" {
  metadata {
    name      = "${var.app_name}-backend-secrets"
    namespace = kubernetes_namespace.tour_app.metadata[0].name
    labels    = local.app_labels
  }

  type = "Opaque"

  data = {
    MONGODB_USERNAME = base64encode("admin")
    MONGODB_PASSWORD = base64encode(random_password.mongodb_password.result)
  }

  depends_on = [kubernetes_namespace.tour_app]
}

# Generate JWT secret
resource "random_password" "jwt_secret" {
  length  = 64
  special = true
}

# Backend Service
resource "kubernetes_service" "backend" {
  metadata {
    name      = "${var.app_name}-backend"
    namespace = kubernetes_namespace.tour_app.metadata[0].name
    labels    = local.app_labels
  }

  spec {
    selector = {
      "app.kubernetes.io/name" = "tour-app-backend"
    }

    port {
      port        = 80
      target_port = var.backend_port
      protocol    = "TCP"
      name        = "http"
    }

    type = "ClusterIP"
  }

  depends_on = [kubernetes_namespace.tour_app]
}

# Backend Deployment
resource "kubernetes_deployment" "backend" {
  metadata {
    name      = "${var.app_name}-backend"
    namespace = kubernetes_namespace.tour_app.metadata[0].name
    labels = merge(
      local.app_labels,
      {
        "app.kubernetes.io/name" = "tour-app-backend"
      }
    )
  }

  spec {
    replicas = var.backend_replicas

    selector {
      match_labels = {
        "app.kubernetes.io/name" = "tour-app-backend"
      }
    }

    template {
      metadata {
        labels = merge(
          local.app_labels,
          {
            "app.kubernetes.io/name" = "tour-app-backend"
          }
        )
      }

      spec {
        container {
          image             = "${var.docker_registry}/tour-app-backend:${var.backend_image_tag}"
          image_pull_policy = "Always"
          name              = "backend"

          port {
            container_port = var.backend_port
            name           = "http"
          }

          env_from {
            config_map_ref {
              name = kubernetes_config_map.backend_config.metadata[0].name
            }
          }

          env_from {
            secret_ref {
              name = kubernetes_secret.backend_secrets.metadata[0].name
            }
          }

          resources {
            requests = {
              cpu    = var.backend_cpu_request
              memory = var.backend_memory_request
            }
            limits = {
              cpu    = var.backend_cpu_limit
              memory = var.backend_memory_limit
            }
          }

          liveness_probe {
            http_get {
              path   = "/auth/me"
              port   = var.backend_port
              scheme = "HTTP"
            }
            initial_delay_seconds = 30
            period_seconds        = 10
            timeout_seconds       = 5
            failure_threshold     = 3
          }

          readiness_probe {
            http_get {
              path   = "/auth/me"
              port   = var.backend_port
              scheme = "HTTP"
            }
            initial_delay_seconds = 10
            period_seconds        = 5
            timeout_seconds       = 3
            failure_threshold     = 2
          }

          volume_mount {
            name       = "uploads"
            mount_path = "/app/uploads"
          }
        }

        volume {
          name = "uploads"
          empty_dir {}
        }

        restart_policy = "Always"

        affinity {
          pod_anti_affinity {
            preferred_during_scheduling_ignored_during_execution {
              weight = 100
              pod_affinity_term {
                label_selector {
                  match_expressions {
                    key      = "app.kubernetes.io/name"
                    operator = "In"
                    values   = ["tour-app-backend"]
                  }
                }
                topology_key = "kubernetes.io/hostname"
              }
            }
          }
        }
      }
    }
  }

  depends_on = [
    kubernetes_namespace.tour_app,
    kubernetes_deployment.mongodb
  ]
}

# Backend Horizontal Pod Autoscaler
resource "kubernetes_horizontal_pod_autoscaler_v2" "backend_hpa" {
  metadata {
    name      = "${var.app_name}-backend-hpa"
    namespace = kubernetes_namespace.tour_app.metadata[0].name
    labels    = local.app_labels
  }

  spec {
    scale_target_ref {
      api_version = "apps/v1"
      kind        = "Deployment"
      name        = kubernetes_deployment.backend.metadata[0].name
    }

    min_replicas = var.backend_replicas
    max_replicas = var.backend_replicas * 3

    metric {
      type = "Resource"
      resource {
        name = "cpu"
        target {
          type                = "Utilization"
          average_utilization = 70
        }
      }
    }

    metric {
      type = "Resource"
      resource {
        name = "memory"
        target {
          type                = "Utilization"
          average_utilization = 80
        }
      }
    }
  }

  depends_on = [kubernetes_namespace.tour_app]
}
