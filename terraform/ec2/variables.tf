variable "aws_region" {
  description = "AWS region for the EC2 test deployment"
  type        = string
  default     = "us-east-1"
}

variable "project_name" {
  description = "Project name prefix for AWS resources"
  type        = string
  default     = "tour-app"
}

variable "environment" {
  description = "Deployment environment label"
  type        = string
  default     = "staging"
}

variable "vpc_id" {
  description = "Optional VPC ID. Defaults to the account default VPC."
  type        = string
  default     = null
}

variable "subnet_id" {
  description = "Optional subnet ID. Defaults to the first subnet in the selected VPC."
  type        = string
  default     = null
}

variable "instance_type" {
  description = "EC2 instance type for the single-node test deployment"
  type        = string
  default     = "t3.medium"
}

variable "root_volume_size" {
  description = "Root EBS volume size in GiB"
  type        = number
  default     = 30
}

variable "key_name" {
  description = "Optional EC2 key pair name for SSH access"
  type        = string
  default     = null
}

variable "ssh_ingress_cidr" {
  description = "CIDR allowed to SSH into the instance"
  type        = string
  default     = "0.0.0.0/0"
}

variable "allocate_eip" {
  description = "Allocate and associate an Elastic IP"
  type        = bool
  default     = true
}

variable "domain_name" {
  description = "Server name for Nginx. Use _ for IP-based testing."
  type        = string
  default     = "_"
}

variable "enable_tls" {
  description = "Enable Let's Encrypt TLS for the configured domain name"
  type        = bool
  default     = false
}

variable "tls_email" {
  description = "Email address used for Let's Encrypt registration when TLS is enabled"
  type        = string
  default     = ""
}

variable "backend_image" {
  description = "Fully-qualified backend Docker image reference"
  type        = string
}

variable "frontend_image" {
  description = "Fully-qualified frontend Docker image reference built with VITE_API_URL=/api"
  type        = string
}

variable "mongo_image" {
  description = "MongoDB Docker image reference"
  type        = string
  default     = "mongo:7"
}

variable "backend_port" {
  description = "Internal backend container port"
  type        = number
  default     = 8808
}

variable "frontend_port" {
  description = "Internal frontend container port"
  type        = number
  default     = 5173
}

variable "database_name" {
  description = "MongoDB database name for the application"
  type        = string
  default     = "tour_app_db"
}

variable "secret_key" {
  description = "Application JWT secret key"
  type        = string
  sensitive   = true
}

variable "frontend_origin" {
  description = "Public frontend origin for backend CORS, e.g. http://ec2-public-ip or https://example.com"
  type        = string
}

variable "backend_debug" {
  description = "Enable backend debug/reload mode"
  type        = bool
  default     = false
}

variable "client_max_body_size" {
  description = "Nginx client_max_body_size value"
  type        = string
  default     = "10m"
}