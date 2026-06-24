variable "kubernetes_namespace" {
  description = "Kubernetes namespace for deployment"
  type        = string
  default     = "tour-app"
}

variable "app_name" {
  description = "Application name"
  type        = string
  default     = "tour-app"
}

variable "environment" {
  description = "Environment (dev, staging, prod)"
  type        = string
  default     = "dev"
}

variable "frontend_url_override" {
  description = "Optional explicit public frontend origin for backend CORS"
  type        = string
  default     = ""
}

# MongoDB variables
variable "mongodb_version" {
  description = "MongoDB version"
  type        = string
  default     = "7.0"
}

variable "mongodb_storage_size" {
  description = "MongoDB storage size"
  type        = string
  default     = "10Gi"
}

variable "mongodb_replica_count" {
  description = "MongoDB replica count (1 for dev, 3+ for prod)"
  type        = number
  default     = 1
}

# Backend variables
variable "backend_replicas" {
  description = "Number of backend pod replicas"
  type        = number
  default     = 2
}

variable "backend_port" {
  description = "Backend port"
  type        = number
  default     = 8808
}

variable "backend_image_tag" {
  description = "Backend Docker image tag"
  type        = string
  default     = "latest"
}

variable "database_name" {
  description = "MongoDB database name used by the application"
  type        = string
  default     = "tour_app_db"
}

# Frontend variables
variable "frontend_replicas" {
  description = "Number of frontend pod replicas"
  type        = number
  default     = 2
}

variable "frontend_port" {
  description = "Frontend port"
  type        = number
  default     = 5173
}

variable "frontend_image_tag" {
  description = "Frontend Docker image tag"
  type        = string
  default     = "latest"
}

# Domain variables
variable "domain_name" {
  description = "Domain name for ingress"
  type        = string
  default     = "tour-app.local"
}

variable "backend_subdomain" {
  description = "Backend subdomain"
  type        = string
  default     = "api"
}

variable "ingress_class_name" {
  description = "Ingress class name"
  type        = string
  default     = "nginx"
}

variable "client_max_body_size" {
  description = "Maximum request body size exposed through ingress"
  type        = string
  default     = "10m"
}

# Resource limits
variable "backend_cpu_request" {
  description = "Backend CPU request"
  type        = string
  default     = "100m"
}

variable "backend_cpu_limit" {
  description = "Backend CPU limit"
  type        = string
  default     = "500m"
}

variable "backend_memory_request" {
  description = "Backend memory request"
  type        = string
  default     = "256Mi"
}

variable "backend_memory_limit" {
  description = "Backend memory limit"
  type        = string
  default     = "512Mi"
}

variable "frontend_cpu_request" {
  description = "Frontend CPU request"
  type        = string
  default     = "50m"
}

variable "frontend_cpu_limit" {
  description = "Frontend CPU limit"
  type        = string
  default     = "200m"
}

variable "frontend_memory_request" {
  description = "Frontend memory request"
  type        = string
  default     = "128Mi"
}

variable "frontend_memory_limit" {
  description = "Frontend memory limit"
  type        = string
  default     = "256Mi"
}

# Image registry
variable "docker_registry" {
  description = "Docker registry URL"
  type        = string
  default     = "docker.io"
}

variable "docker_registry_username" {
  description = "Docker registry username"
  type        = string
  default     = ""
  sensitive   = true
}

variable "docker_registry_password" {
  description = "Docker registry password"
  type        = string
  default     = ""
  sensitive   = true
}

variable "docker_registry_email" {
  description = "Docker registry email"
  type        = string
  default     = ""
  sensitive   = true
}
