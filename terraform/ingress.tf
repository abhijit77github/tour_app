# Ingress for routing traffic
resource "kubernetes_ingress_v1" "tour_app" {
  metadata {
    name      = "${var.app_name}-ingress"
    namespace = kubernetes_namespace.tour_app.metadata[0].name
    labels    = local.app_labels

    annotations = {
      "nginx.ingress.kubernetes.io/rewrite-target" = "/"
      "nginx.ingress.kubernetes.io/proxy-body-size" = "10m"
    }
  }

  spec {
    ingress_class_name = "nginx"

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

        path {
          path      = "/api"
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
    kubernetes_service.frontend,
    kubernetes_service.backend
  ]
}

# Optional: TLS Certificate (requires cert-manager)
# Uncomment and customize if using cert-manager
/*
resource "kubernetes_ingress_v1" "tour_app_tls" {
  metadata {
    name      = "${var.app_name}-ingress-tls"
    namespace = kubernetes_namespace.tour_app.metadata[0].name
    labels    = local.app_labels

    annotations = {
      "cert-manager.io/cluster-issuer" = "letsencrypt-prod"
    }
  }

  spec {
    tls {
      hosts = [
        var.domain_name,
        "${var.backend_subdomain}.${var.domain_name}"
      ]
      secret_name = "${var.app_name}-tls-cert"
    }

    ingress_class_name = "nginx"

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

        path {
          path      = "/api"
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
}
*/
