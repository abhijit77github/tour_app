# Kubernetes Deployment with Terraform

This directory contains Terraform configuration for deploying the Tour App to Kubernetes in a platform-agnostic way.

Important runtime assumptions for this stack:
- the backend uses `MONGODB_URL`, `DATABASE_NAME`, `SECRET_KEY`, and `FRONTEND_URL`
- the frontend image must be built with `VITE_API_URL=/api`
- ingress serves the SPA at `/` and strips `/api/` before forwarding to FastAPI

## Prerequisites

1. **Kubernetes Cluster**: Any Kubernetes cluster (local, AWS EKS, GCP GKE, Azure AKS, etc.)
2. **kubectl**: Installed and configured to connect to your cluster
3. **Terraform**: Version 1.0 or higher
4. **Docker Images**: Backend and frontend Docker images pushed to a registry

## Configuration Files

- `main.tf` - Terraform provider and namespace configuration
- `variables.tf` - All configurable variables
- `database.tf` - MongoDB deployment
- `backend.tf` - FastAPI backend deployment
- `frontend.tf` - Vue.js frontend deployment
- `ingress.tf` - Ingress configuration for routing
- `outputs.tf` - Terraform outputs (service URLs, kubectl commands, etc.)
- `mongodb-init.js` - MongoDB initialization script
- `nginx.conf.tpl` - Nginx configuration template
- `terraform.tfvars.example` - Example variables file

## Quick Start

### 1. Prepare Docker Images

Build and push Docker images to your registry:

```bash
# Build backend image
cd backend
docker build -t your-registry/tour-app-backend:latest .
docker push your-registry/tour-app-backend:latest

# Build frontend image
cd ../frontend
docker build --build-arg VITE_API_URL=/api -t your-registry/tour-app-frontend:latest .
docker push your-registry/tour-app-frontend:latest
```

### 2. Set Up Terraform Variables

```bash
cd terraform
cp terraform.tfvars.example terraform.tfvars
```

Edit `terraform.tfvars` to customize:
- Docker registry and image paths
- Replica counts
- Resource limits
- Domain names
- Storage sizes

Example for AWS EKS:
```hcl
kubernetes_namespace = "tour-app"
docker_registry      = "123456789.dkr.ecr.us-east-1.amazonaws.com"
backend_image_tag    = "v1.0.0"
frontend_image_tag   = "v1.0.0"
backend_replicas     = 3
frontend_replicas    = 3
domain_name          = "tour-app.example.com"
```

### 3. Initialize Terraform

```bash
terraform init
```

### 4. Plan Deployment

```bash
terraform plan -out=tfplan
```

Review the planned changes.

### 5. Apply Configuration

```bash
terraform apply tfplan
```

Terraform will create:
- Kubernetes namespace
- MongoDB with persistent storage
- Backend deployment with HPA
- Frontend deployment with HPA
- Services for each component
- Ingress for routing

### 6. Verify Deployment

```bash
# View outputs
terraform output

# Check pods
kubectl get pods -n tour-app

# Check services
kubectl get svc -n tour-app

# Check ingress
kubectl get ingress -n tour-app

# View logs
kubectl logs -f deployment/tour-app-backend -n tour-app
kubectl logs -f deployment/tour-app-frontend -n tour-app
```

## Platform-Specific Setup

### Local Kubernetes (Docker Desktop / Minikube)

```hcl
# terraform.tfvars
kubernetes_namespace = "tour-app"
docker_registry      = "docker.io"
backend_replicas     = 1
frontend_replicas    = 1
mongodb_replica_count = 1
domain_name          = "localhost"
```

Access via `http://localhost` (port-forward if needed)

### AWS EKS

```hcl
kubernetes_namespace = "tour-app"
docker_registry      = "123456789.dkr.ecr.us-east-1.amazonaws.com"
backend_replicas     = 3
frontend_replicas    = 3
mongodb_replica_count = 3
domain_name          = "your-domain.com"
```

Update `main.tf` provider to use EKS authentication:

```hcl
provider "kubernetes" {
  host                   = aws_eks_cluster.main.endpoint
  cluster_ca_certificate = base64decode(aws_eks_cluster.main.certificate_authority[0].data)
  token                  = data.aws_eks_auth.main.token
}
```

### GCP GKE

```hcl
kubernetes_namespace = "tour-app"
docker_registry      = "gcr.io/your-project"
backend_replicas     = 3
frontend_replicas    = 3
mongodb_replica_count = 3
domain_name          = "your-domain.com"
```

Update `main.tf` provider:

```hcl
provider "kubernetes" {
  host                   = "https://${google_container_cluster.main.endpoint}"
  cluster_ca_certificate = base64decode(google_container_cluster.main.master_auth[0].cluster_ca_certificate)
  token                  = data.google_client_config.default.access_token
}
```

### Azure AKS

```hcl
kubernetes_namespace = "tour-app"
docker_registry      = "your-acr-name.azurecr.io"
backend_replicas     = 3
frontend_replicas    = 3
mongodb_replica_count = 3
domain_name          = "your-domain.com"
```

## Useful Commands

```bash
# View deployment info
terraform output deployment_info

# Get kubectl commands
terraform output kubectl_commands

# Port forward to access services locally
kubectl port-forward svc/tour-app-backend 8808:80 -n tour-app
kubectl port-forward svc/tour-app-frontend 5173:80 -n tour-app
kubectl port-forward svc/mongodb 27017:27017 -n tour-app

# Scale deployments
kubectl scale deployment tour-app-backend --replicas=5 -n tour-app

# View HPA status
kubectl get hpa -n tour-app

# Check MongoDB connection
mongosh --host mongodb.<namespace>.svc.cluster.local --username admin --password <password>

# View ingress details
kubectl get ingress -n tour-app -o yaml

# Delete deployment
terraform destroy
```

## Environment Variables

### Backend

Set in `backend.tf` ConfigMap/Secret:
- `MONGODB_URL` - MongoDB connection string with `authSource=admin`
- `DATABASE_NAME` - Database name (default: `tour_app_db`)
- `SECRET_KEY` - JWT signing secret (auto-generated)
- `FRONTEND_URL` - Public frontend origin for CORS
- `HOST` - Bind address
- `PORT` - Backend port (default: 8808)
- `DEBUG` - FastAPI debug flag

### Frontend

Build-time requirement:
- `VITE_API_URL=/api` when building the frontend image used by Kubernetes

## Security Considerations

1. **Secrets**: MongoDB credentials and JWT secret are generated randomly and stored as Kubernetes Secrets
2. **RBAC**: Apply appropriate RBAC policies to the namespace
3. **Network Policies**: Consider adding network policies to restrict traffic
4. **TLS**: Add cert-manager-managed TLS or your platform's ingress TLS after the base HTTP path is validated
5. **Private Registry**: Use private Docker registry with auth secrets if needed

## Scaling

The deployments include Horizontal Pod Autoscalers (HPA) that automatically scale based on:
- CPU utilization (70% threshold)
- Memory utilization (80% threshold)

To disable HPA and use fixed replicas:
```bash
terraform apply -var="backend_replicas=1" -var="frontend_replicas=1"
```

## Troubleshooting

### Pods not starting

```bash
kubectl describe pod <pod-name> -n tour-app
kubectl logs <pod-name> -n tour-app
```

### MongoDB connection issues

```bash
# Test MongoDB connectivity from pod
kubectl exec -it <pod-name> -n tour-app -- mongosh --host mongodb --username admin --password <password>
```

### Ingress not working

```bash
# Check ingress status
kubectl get ingress -n tour-app
kubectl describe ingress tour-app-frontend-ingress -n tour-app
kubectl describe ingress tour-app-api-ingress -n tour-app

# Ensure ingress controller is installed
kubectl get pods -n ingress-nginx
```

### High memory usage

Adjust resource limits in `terraform.tfvars`:

```hcl
backend_memory_limit  = "1Gi"
frontend_memory_limit = "512Mi"
```

## Production Checklist

- [ ] Use production-grade Kubernetes cluster (3+ nodes)
- [ ] Configure MongoDB with replication (replica_count >= 3)
- [ ] Enable TLS for ingress (uncomment in ingress.tf)
- [ ] Set up monitoring and logging (Prometheus, ELK, etc.)
- [ ] Configure persistent storage for MongoDB (not emptyDir)
- [ ] Set resource limits and requests appropriately
- [ ] Enable RBAC and network policies
- [ ] Use private Docker registry
- [ ] Set up backup strategy for MongoDB
- [ ] Configure alerting and incident response
- [ ] Test disaster recovery procedures
- [ ] Document runbooks for common operations

## Cleanup

```bash
# Destroy all resources created by Terraform
terraform destroy

# Or selectively destroy
terraform destroy -var="kubernetes_namespace=tour-app"
```

## Support

For issues or questions about the Terraform configuration, refer to:
- [Kubernetes Terraform Provider Documentation](https://registry.terraform.io/providers/hashicorp/kubernetes/latest/docs)
- [Terraform Best Practices](https://www.terraform.io/cloud-docs/recommended-practices)
- Project README and documentation
