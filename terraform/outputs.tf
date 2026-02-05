output "kubernetes_namespace" {
  description = "Kubernetes namespace where the app is deployed"
  value       = kubernetes_namespace.tour_app.metadata[0].name
}

output "backend_service_name" {
  description = "Backend service name"
  value       = kubernetes_service.backend.metadata[0].name
}

output "backend_service_url" {
  description = "Backend service internal URL"
  value       = "http://${kubernetes_service.backend.metadata[0].name}:80"
}

output "frontend_service_name" {
  description = "Frontend service name"
  value       = kubernetes_service.frontend.metadata[0].name
}

output "frontend_service_url" {
  description = "Frontend service internal URL"
  value       = "http://${kubernetes_service.frontend.metadata[0].name}:80"
}

output "mongodb_service_name" {
  description = "MongoDB service name"
  value       = kubernetes_service.mongodb.metadata[0].name
}

output "mongodb_service_url" {
  description = "MongoDB connection string"
  value       = "mongodb://admin:${random_password.mongodb_password.result}@${kubernetes_service.mongodb.metadata[0].name}:${local.mongodb_port}/tour_app?authSource=admin"
  sensitive   = true
}

output "ingress_hosts" {
  description = "Ingress hosts configuration"
  value = {
    main_domain        = var.domain_name
    backend_subdomain  = "${var.backend_subdomain}.${var.domain_name}"
  }
}

output "deployment_info" {
  description = "Deployment information"
  value = {
    app_name    = var.app_name
    environment = var.environment
    namespace   = kubernetes_namespace.tour_app.metadata[0].name
    
    backend = {
      image      = "${var.docker_registry}/tour-app-backend:${var.backend_image_tag}"
      replicas   = var.backend_replicas
      port       = var.backend_port
      service    = kubernetes_service.backend.metadata[0].name
    }
    
    frontend = {
      image    = "${var.docker_registry}/tour-app-frontend:${var.frontend_image_tag}"
      replicas = var.frontend_replicas
      port     = var.frontend_port
      service  = kubernetes_service.frontend.metadata[0].name
    }
    
    mongodb = {
      service = kubernetes_service.mongodb.metadata[0].name
      port    = local.mongodb_port
    }
  }
}

output "kubectl_commands" {
  description = "Useful kubectl commands for managing the deployment"
  value = {
    view_pods               = "kubectl get pods -n ${kubernetes_namespace.tour_app.metadata[0].name}"
    view_services           = "kubectl get svc -n ${kubernetes_namespace.tour_app.metadata[0].name}"
    view_deployments        = "kubectl get deployments -n ${kubernetes_namespace.tour_app.metadata[0].name}"
    backend_logs            = "kubectl logs -f deployment/${var.app_name}-backend -n ${kubernetes_namespace.tour_app.metadata[0].name}"
    frontend_logs           = "kubectl logs -f deployment/${var.app_name}-frontend -n ${kubernetes_namespace.tour_app.metadata[0].name}"
    mongodb_logs            = "kubectl logs -f deployment/mongodb -n ${kubernetes_namespace.tour_app.metadata[0].name}"
    describe_backend        = "kubectl describe deployment ${var.app_name}-backend -n ${kubernetes_namespace.tour_app.metadata[0].name}"
    port_forward_backend    = "kubectl port-forward svc/${kubernetes_service.backend.metadata[0].name} 8808:80 -n ${kubernetes_namespace.tour_app.metadata[0].name}"
    port_forward_frontend   = "kubectl port-forward svc/${kubernetes_service.frontend.metadata[0].name} 5173:80 -n ${kubernetes_namespace.tour_app.metadata[0].name}"
    port_forward_mongodb    = "kubectl port-forward svc/mongodb 27017:27017 -n ${kubernetes_namespace.tour_app.metadata[0].name}"
    scale_backend           = "kubectl scale deployment ${var.app_name}-backend --replicas=3 -n ${kubernetes_namespace.tour_app.metadata[0].name}"
    scale_frontend          = "kubectl scale deployment ${var.app_name}-frontend --replicas=3 -n ${kubernetes_namespace.tour_app.metadata[0].name}"
  }
}
