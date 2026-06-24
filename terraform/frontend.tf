# Frontend Service
resource "kubernetes_service" "frontend" {
  metadata {
    name      = "${var.app_name}-frontend"
    namespace = kubernetes_namespace.tour_app.metadata[0].name
    labels    = local.app_labels
  }

  spec {
    selector = {
      "app.kubernetes.io/name" = "tour-app-frontend"
    }

    port {
      port        = 80
      target_port = var.frontend_port
      protocol    = "TCP"
      name        = "http"
    }

    type = "ClusterIP"
  }

  depends_on = [kubernetes_namespace.tour_app]
}

# Frontend Deployment
resource "kubernetes_deployment" "frontend" {
  metadata {
    name      = "${var.app_name}-frontend"
    namespace = kubernetes_namespace.tour_app.metadata[0].name
    labels = merge(
      local.app_labels,
      {
        "app.kubernetes.io/name" = "tour-app-frontend"
      }
    )
  }

  spec {
    replicas = var.frontend_replicas

    selector {
      match_labels = {
        "app.kubernetes.io/name" = "tour-app-frontend"
      }
    }

    template {
      metadata {
        labels = merge(
          local.app_labels,
          {
            "app.kubernetes.io/name" = "tour-app-frontend"
          }
        )
      }

      spec {
        container {
          image             = "${var.docker_registry}/tour-app-frontend:${var.frontend_image_tag}"
          image_pull_policy = "Always"
          name              = "frontend"

          port {
            container_port = var.frontend_port
            name           = "http"
          }

          resources {
            requests = {
              cpu    = var.frontend_cpu_request
              memory = var.frontend_memory_request
            }
            limits = {
              cpu    = var.frontend_cpu_limit
              memory = var.frontend_memory_limit
            }
          }

          liveness_probe {
            http_get {
              path   = "/"
              port   = var.frontend_port
              scheme = "HTTP"
            }
            initial_delay_seconds = 30
            period_seconds        = 10
            timeout_seconds       = 5
            failure_threshold     = 3
          }

          readiness_probe {
            http_get {
              path   = "/"
              port   = var.frontend_port
              scheme = "HTTP"
            }
            initial_delay_seconds = 10
            period_seconds        = 5
            timeout_seconds       = 3
            failure_threshold     = 2
          }
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
                    values   = ["tour-app-frontend"]
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
    kubernetes_deployment.backend
  ]
}

# Frontend Horizontal Pod Autoscaler
resource "kubernetes_horizontal_pod_autoscaler_v2" "frontend_hpa" {
  metadata {
    name      = "${var.app_name}-frontend-hpa"
    namespace = kubernetes_namespace.tour_app.metadata[0].name
    labels    = local.app_labels
  }

  spec {
    scale_target_ref {
      api_version = "apps/v1"
      kind        = "Deployment"
      name        = kubernetes_deployment.frontend.metadata[0].name
    }

    min_replicas = var.frontend_replicas
    max_replicas = var.frontend_replicas * 3

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
