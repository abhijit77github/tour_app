# Frontend ingress for SPA traffic.
resource "kubernetes_ingress_v1" "tour_app_frontend" {
  metadata {
    name      = "${var.app_name}-frontend-ingress"
    namespace = kubernetes_namespace.tour_app.metadata[0].name
    labels    = local.app_labels

    annotations = {
      "nginx.ingress.kubernetes.io/proxy-body-size" = var.client_max_body_size
    }
  }

  spec {
    ingress_class_name = var.ingress_class_name

    rule {
      host = var.domain_name

      http {
        path {
          path     = "/"
          path_type = "Prefix"

          backend {
            service {
              name = kubernetes_service.frontend.metadata[0].name
              port {
                number = 80
              }
            }
          }
        }

      }
    }
  }


  depends_on = [
    kubernetes_namespace.tour_app,
    kubernetes_service.frontend
  ]
}

# API ingress strips /api/ before forwarding to FastAPI.
resource "kubernetes_ingress_v1" "tour_app_api" {
  metadata {
    name      = "${var.app_name}-api-ingress"
    namespace = kubernetes_namespace.tour_app.metadata[0].name
    labels    = local.app_labels

    annotations = {
      "nginx.ingress.kubernetes.io/use-regex"       = "true"
      "nginx.ingress.kubernetes.io/rewrite-target"  = "/$2"
      "nginx.ingress.kubernetes.io/proxy-body-size" = var.client_max_body_size
    }
  }

  spec {
    ingress_class_name = var.ingress_class_name

    rule {
      host = var.domain_name

      http {
        path {
          path      = "/api(/|$)(.*)"
          path_type = "ImplementationSpecific"

          backend {
            service {
              name = kubernetes_service.backend.metadata[0].name
              port {
                number = 80
              }
            }
          }
        }
      }
    }
  }

  depends_on = [
    kubernetes_namespace.tour_app,
    kubernetes_service.backend
  ]
}

# Optional direct backend host for docs or debugging.
resource "kubernetes_ingress_v1" "tour_app_backend" {
  metadata {
    name      = "${var.app_name}-backend-ingress"
    namespace = kubernetes_namespace.tour_app.metadata[0].name
    labels    = local.app_labels

    annotations = {
      "nginx.ingress.kubernetes.io/proxy-body-size" = var.client_max_body_size
    }
  }

  spec {
    ingress_class_name = var.ingress_class_name

    rule {
      host = "${var.backend_subdomain}.${var.domain_name}"

      http {
        path {
          path     = "/"
          path_type = "Prefix"

          backend {
            service {
              name = kubernetes_service.backend.metadata[0].name
              port {
                number = 80
              }
            }
          }
        }
      }
    }
  }

  depends_on = [
    kubernetes_namespace.tour_app,
    kubernetes_service.backend
  ]
}
