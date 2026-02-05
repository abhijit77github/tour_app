# Tour App Kubernetes Deployment Guide

## Overview

This guide provides step-by-step instructions for deploying the Tour App to any Kubernetes cluster using Terraform. The infrastructure is platform-agnostic and works with:

- Local clusters (Docker Desktop, Minikube)
- AWS EKS
- Google Cloud GKE
- Azure AKS
- Self-managed Kubernetes
- Any other Kubernetes distribution

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                   Kubernetes Cluster                 │
│                                                       │
│  ┌──────────────────────────────────────────────┐   │
│  │ Ingress (NGINX)                              │   │
│  │ ├─ route.example.com → Frontend              │   │
│  │ └─ api.route.example.com → Backend           │   │
│  └───────┬────────────────┬──────────────────────┘   │
│          │                │                           │
│   ┌──────▼─────────┐  ┌───▼────────────────┐         │
│   │   Frontend     │  │   Backend          │         │
│   │  Deployment    │  │  Deployment        │         │
│   │ (Vue.js, 2×)   │  │ (FastAPI, 2×)      │         │
│   │   + HPA        │  │   + HPA             │         │
│   └────────────────┘  │  + Secrets          │         │
│                       │  + ConfigMap        │         │
│                       └───────┬─────────────┘         │
│                               │                       │
│                       ┌───────▼──────────┐            │
│                       │  MongoDB         │            │
│                       │  StatefulSet     │            │
│                       │  + PersistentVol │            │
│                       │  + Secrets       │            │
│                       └──────────────────┘            │
│                                                       │
└─────────────────────────────────────────────────────┘
```

## Step 1: Prerequisites

### Required Tools

```bash
# Check kubectl version
kubectl version --client

# Check Terraform version  
terraform version

# Check Docker (for building images)
docker version
```

Versions needed:
- Kubernetes: 1.24+
- Terraform: 1.0+
- kubectl: any recent version
- Docker: 20.10+ (for building images)

### Kubernetes Cluster

Ensure you have access to a Kubernetes cluster. Examples:

**Local (Docker Desktop):**
- Enable Kubernetes in Docker Desktop settings
- No additional setup needed

**Local (Minikube):**
```bash
minikube start --memory=4096 --cpus=4
minikube addons enable ingress
```

**AWS EKS:**
```bash
# Install eksctl
brew install eksctl

# Create cluster
eksctl create cluster --name tour-app --region us-east-1 --nodes 3
```

**GCP GKE:**
```bash
# Install gcloud CLI
curl https://sdk.cloud.google.com | bash

# Create cluster
gcloud container clusters create tour-app --zone us-central1-a --num-nodes 3
```

**Azure AKS:**
```bash
# Install az CLI
brew install azure-cli

# Create resource group and cluster
az group create --name tour-app-rg --location eastus
az aks create --resource-group tour-app-rg --name tour-app --node-count 3
```

Verify cluster access:

```bash
kubectl cluster-info
kubectl get nodes
```

## Step 2: Build Docker Images

### Backend Image

```bash
cd backend

# Build image
docker build -t tour-app-backend:latest .

# Tag for registry (e.g., Docker Hub)
docker tag tour-app-backend:latest your-username/tour-app-backend:latest

# Push to registry
docker push your-username/tour-app-backend:latest

cd ..
```

### Frontend Image

```bash
cd frontend

# Build image
docker build -t tour-app-frontend:latest .

# Tag for registry
docker tag tour-app-frontend:latest your-username/tour-app-frontend:latest

# Push to registry
docker push your-username/tour-app-frontend:latest

cd ..
```

### For Cloud Registries

**AWS ECR:**
```bash
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin 123456789.dkr.ecr.us-east-1.amazonaws.com

docker tag tour-app-backend:latest 123456789.dkr.ecr.us-east-1.amazonaws.com/tour-app-backend:latest
docker push 123456789.dkr.ecr.us-east-1.amazonaws.com/tour-app-backend:latest
```

**GCP GCR:**
```bash
gcloud auth configure-docker

docker tag tour-app-backend:latest gcr.io/your-project/tour-app-backend:latest
docker push gcr.io/your-project/tour-app-backend:latest
```

**Azure ACR:**
```bash
az acr login --name youracrname

docker tag tour-app-backend:latest youracrname.azurecr.io/tour-app-backend:latest
docker push youracrname.azurecr.io/tour-app-backend:latest
```

## Step 3: Configure Terraform

```bash
cd terraform

# Copy example variables
cp terraform.tfvars.example terraform.tfvars

# Edit variables for your environment
nano terraform.tfvars  # or use your preferred editor
```

### Example Configurations

**Development (Local Cluster):**
```hcl
kubernetes_namespace  = "tour-app"
app_name              = "tour-app"
environment           = "dev"
backend_replicas      = 1
frontend_replicas     = 1
mongodb_replica_count = 1
mongodb_storage_size  = "5Gi"
domain_name           = "localhost"
docker_registry       = "docker.io"
backend_image_tag     = "latest"
frontend_image_tag    = "latest"
```

**Staging (AWS EKS):**
```hcl
kubernetes_namespace  = "tour-app-staging"
app_name              = "tour-app"
environment           = "staging"
backend_replicas      = 2
frontend_replicas     = 2
mongodb_replica_count = 2
mongodb_storage_size  = "50Gi"
domain_name           = "staging.tour-app.com"
docker_registry       = "123456789.dkr.ecr.us-east-1.amazonaws.com"
backend_image_tag     = "v1.0.0-staging"
frontend_image_tag    = "v1.0.0-staging"
```

**Production (GKE):**
```hcl
kubernetes_namespace  = "tour-app-prod"
app_name              = "tour-app"
environment           = "prod"
backend_replicas      = 3
frontend_replicas     = 3
mongodb_replica_count = 3
mongodb_storage_size  = "200Gi"
domain_name           = "tour-app.com"
docker_registry       = "gcr.io/your-project"
backend_image_tag     = "v1.0.0"
frontend_image_tag    = "v1.0.0"
backend_cpu_limit     = "1000m"
backend_memory_limit  = "1Gi"
```

## Step 4: Initialize Terraform

```bash
cd terraform

# Initialize Terraform working directory
terraform init

# This will:
# - Download required providers (Kubernetes, Helm)
# - Set up state management
# - Create .terraform directory
```

## Step 5: Plan Deployment

```bash
# Generate execution plan
terraform plan -out=tfplan

# Review the output to see:
# - What resources will be created
# - ConfigMaps, Secrets, Deployments
# - Services and Ingress configuration
```

Expected output:

```
Terraform will perform the following actions:

  # kubernetes_namespace.tour_app will be created
  + resource "kubernetes_namespace" "tour_app" {
      + id = (known after apply)
      + metadata {
          + generation       = (known after apply)
          + name             = "tour-app"
          + resource_version = (known after apply)
          ...

  # kubernetes_deployment.mongodb will be created
  + resource "kubernetes_deployment" "mongodb" {
      ...

  # kubernetes_deployment.backend will be created
  + resource "kubernetes_deployment" "backend" {
      ...

  # kubernetes_deployment.frontend will be created
  + resource "kubernetes_deployment" "frontend" {
      ...

Plan: 25 resources to add, 0 to change, 0 to destroy.
```

## Step 6: Apply Configuration

```bash
# Apply the plan
terraform apply tfplan

# This will create all resources. Wait for completion (5-10 minutes typically)
```

Once complete, you'll see output with:
- Service names and URLs
- Namespace information
- Helpful kubectl commands

## Step 7: Verify Deployment

```bash
# Get all outputs
terraform output

# Check pods status
kubectl get pods -n tour-app

# Expected output:
# NAME                                  READY   STATUS    RESTARTS   AGE
# mongodb-xxxxxxxx-xxxxx                1/1     Running   0          2m
# tour-app-backend-xxxxxxxx-xxxxx       1/1     Running   0          1m
# tour-app-backend-xxxxxxxx-xxxxx       1/1     Running   0          1m
# tour-app-frontend-xxxxxxxx-xxxxx      1/1     Running   0          1m
# tour-app-frontend-xxxxxxxx-xxxxx      1/1     Running   0          1m

# Check services
kubectl get svc -n tour-app

# Check deployments
kubectl get deployments -n tour-app

# Check ingress
kubectl get ingress -n tour-app
```

## Step 8: Access the Application

### Local Testing

```bash
# Port-forward to access services
kubectl port-forward -n tour-app svc/tour-app-frontend 5173:80 &
kubectl port-forward -n tour-app svc/tour-app-backend 8808:80 &

# Access in browser:
# Frontend: http://localhost:5173
# Backend API: http://localhost:8808
```

### Using Ingress

For local development, add entry to `/etc/hosts`:

```bash
# For localhost
127.0.0.1 tour-app.local api.tour-app.local

# For remote cluster, use cluster's IP
```

Then access:
- Frontend: http://tour-app.local
- Backend API: http://api.tour-app.local

### Cloud Ingress (AWS/GCP/Azure)

Get ingress IP:

```bash
kubectl get ingress tour-app-ingress -n tour-app -o wide

# For AWS ELB or Google Load Balancer:
# The EXTERNAL-IP will show the public endpoint

# Update your DNS records to point to this IP
```

## Monitoring & Management

### View Logs

```bash
# Backend logs
kubectl logs -f deployment/tour-app-backend -n tour-app

# Frontend logs
kubectl logs -f deployment/tour-app-frontend -n tour-app

# MongoDB logs
kubectl logs -f deployment/mongodb -n tour-app

# Follow logs from all pods
kubectl logs -f -l app.kubernetes.io/name=tour-app -n tour-app
```

### Check Pod Status

```bash
# Describe specific pod
kubectl describe pod <pod-name> -n tour-app

# Get events
kubectl get events -n tour-app --sort-by='.lastTimestamp'
```

### Database Access

```bash
# Port-forward to MongoDB
kubectl port-forward -n tour-app svc/mongodb 27017:27017 &

# Connect with mongosh
mongosh mongodb://admin:PASSWORD@localhost:27017/tour_app?authSource=admin

# Or get password from secret
kubectl get secret tour-app-mongodb-credentials -n tour-app -o jsonpath='{.data.password}' | base64 -d
```

### Scale Deployments

```bash
# Scale backend to 5 replicas
kubectl scale deployment tour-app-backend --replicas=5 -n tour-app

# Check HPA status
kubectl get hpa -n tour-app
kubectl describe hpa tour-app-backend-hpa -n tour-app
```

## Troubleshooting

### Pods Stuck in Pending

```bash
kubectl describe pod <pod-name> -n tour-app
# Check events section for resource constraints
# May need more nodes or adjust resource requests
```

### Ingress Not Working

```bash
# Check ingress status
kubectl describe ingress tour-app-ingress -n tour-app

# Verify ingress controller is installed
kubectl get pods -n ingress-nginx

# For local, install ingress controller
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/controller-v1.8.1/deploy/static/provider/local/deploy.yaml
```

### Database Connection Errors

```bash
# Test MongoDB connectivity
kubectl run -it --rm debug --image=mongo:latest --restart=Never -n tour-app -- \
  mongosh --host mongodb --username admin --password $(kubectl get secret tour-app-mongodb-credentials -n tour-app -o jsonpath='{.data.password}' | base64 -d)
```

### Image Pull Errors

```bash
# Check image pull secrets
kubectl get secrets -n tour-app

# Verify image is accessible
docker pull your-registry/tour-app-backend:latest

# For private registries, create secret:
kubectl create secret docker-registry regcred \
  --docker-server=your-registry \
  --docker-username=username \
  --docker-password=password \
  -n tour-app
```

## Updating the Application

### Update Backend Image

```bash
# Build and push new image
docker build -t your-registry/tour-app-backend:v1.0.1 backend/
docker push your-registry/tour-app-backend:v1.0.1

# Update Terraform variable
terraform apply -var="backend_image_tag=v1.0.1"
```

### Update Frontend Image

```bash
# Build and push new image
docker build -t your-registry/tour-app-frontend:v1.0.1 frontend/
docker push your-registry/tour-app-frontend:v1.0.1

# Update Terraform variable
terraform apply -var="frontend_image_tag=v1.0.1"
```

## Cleanup

### Remove All Resources

```bash
cd terraform

# Destroy all Terraform-managed resources
terraform destroy

# This will delete:
# - Deployments
# - Services
# - Ingress
# - ConfigMaps and Secrets
# - Namespace (if not protected)
# - Persistent Volumes
```

### Partial Cleanup

```bash
# Destroy only backend (keep database)
terraform destroy -target=kubernetes_deployment.backend

# Destroy specific resource
terraform destroy -target=kubernetes_deployment.frontend
```

## Next Steps

1. Set up monitoring (Prometheus, Grafana)
2. Configure logging (ELK Stack, CloudWatch, etc.)
3. Set up CI/CD pipeline (GitHub Actions, GitLab CI, etc.)
4. Configure backup strategy for MongoDB
5. Set up RBAC policies
6. Enable network policies
7. Configure resource quotas
8. Set up alerts and notifications
9. Document runbooks for common operations
10. Test disaster recovery procedures

## Support & Resources

- [Terraform Kubernetes Provider](https://registry.terraform.io/providers/hashicorp/kubernetes/latest/docs)
- [Kubernetes Documentation](https://kubernetes.io/docs/)
- [MongoDB Kubernetes Operator](https://www.mongodb.com/kubernetes)
- [Ingress NGINX Controller](https://kubernetes.github.io/ingress-nginx/)
