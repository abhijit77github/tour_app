# EC2 Test Deployment with Nginx Reverse Proxy

This Terraform stack provisions a single EC2 instance for first-pass deployment validation.

The instance bootstraps:
- Docker Engine + Docker Compose plugin
- Nginx on the host
- MongoDB, backend, frontend, and seed containers via Docker Compose
- Nginx reverse proxy in front of the frontend and backend
- optional Let's Encrypt TLS when a real domain is pointed at the instance

## What this path is for

Use this stack before Kubernetes to validate:
- image startup and health
- MongoDB connectivity
- `VITE_API_URL=/api` frontend behavior
- Nginx reverse proxy routing
- auth and upload flows behind a single public endpoint

## What you need first

1. Build and push the backend image.
2. Build and push the frontend image with `VITE_API_URL=/api`.
3. Choose an AWS region, subnet, and SSH key pair if needed.
4. Decide the public frontend origin you want the backend to allow for CORS.
5. If enabling TLS, point an A record for your domain at the instance public IP before running `terraform apply`.

Example frontend build:

```bash
docker build \
  --build-arg VITE_API_URL=/api \
  -t your-registry/tour-app-frontend:ec2-test \
  ./frontend
docker push your-registry/tour-app-frontend:ec2-test
```

Example backend build:

```bash
docker build -t your-registry/tour-app-backend:ec2-test ./backend
docker push your-registry/tour-app-backend:ec2-test
```

## Files

- `main.tf` - AWS provider, EC2 instance, security group, optional Elastic IP
- `variables.tf` - configurable deployment inputs
- `outputs.tf` - public IP, URL, and SSH helper
- `templates/docker-compose.yml.tftpl` - app stack rendered onto the instance
- `templates/nginx.conf.tftpl` - host-level reverse proxy config
- `templates/user_data.sh.tftpl` - bootstrap script run at first boot

## Quick start

Create `terraform.tfvars` in this directory:

```hcl
aws_region      = "us-east-1"
instance_type   = "t3.medium"
key_name        = "your-keypair"
ssh_ingress_cidr = "YOUR_IP/32"

backend_image   = "your-registry/tour-app-backend:ec2-test"
frontend_image  = "your-registry/tour-app-frontend:ec2-test"

secret_key      = "replace-with-a-long-random-secret"
frontend_origin = "http://YOUR_EC2_PUBLIC_IP"
domain_name     = "_"
enable_tls      = false
tls_email       = ""
```

Deploy:

```bash
cd terraform/ec2
terraform init
terraform plan -out=tfplan
terraform apply tfplan
```

After apply:

```bash
terraform output app_url
terraform output ssh_command
```

## Runtime layout

- `http://<host>/` -> frontend container on `127.0.0.1:5173`
- `http://<host>/api/` -> backend container on `127.0.0.1:8808`
- MongoDB stays private inside Docker networking

Nginx strips the `/api/` prefix before forwarding, so backend routes like `/auth/login` continue to work unchanged.

If `enable_tls = true`, Nginx will terminate HTTPS on port 443 and redirect HTTP to HTTPS after Certbot issues a certificate.

## Operational notes

- The bootstrap process writes app files to `/opt/tour-app`
- Compose stack name is `tour-app`
- Nginx config lives at `/etc/nginx/conf.d/tour-app.conf`
- MongoDB data is stored in a Docker volume on the instance
- The seed container runs `python -m backend.scripts.seed_local_dev` once on boot

## First checks after deploy

```bash
ssh ubuntu@<public-ip>
cd /opt/tour-app
docker compose ps
docker compose logs backend --tail=100
curl http://127.0.0.1:8808/health
curl http://127.0.0.1:5173/
curl http://127.0.0.1/api/health
sudo systemctl status nginx
```

## Limits of this path

- single instance only
- local MongoDB only
- no autoscaling
- no centralized logs or metrics

This is intentional: it is a validation path before moving to the Kubernetes stack.