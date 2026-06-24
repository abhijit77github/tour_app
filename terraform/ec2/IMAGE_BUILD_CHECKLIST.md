# EC2 Image Build Checklist

Use this checklist before running the EC2 deployment.

## Frontend image

- Build the frontend image with `VITE_API_URL=/api`.
- Confirm the image tag you build is the same one referenced in `terraform.tfvars`.
- Verify the container responds on port `5173`.
- Verify the container serves the built SPA root at `/`.
- Do not rely on runtime `VITE_API_URL`; Vite bakes it at build time.

Example:

```bash
docker build \
  --build-arg VITE_API_URL=/api \
  -t your-registry/tour-app-frontend:ec2-test \
  ./frontend
docker push your-registry/tour-app-frontend:ec2-test
```

## Backend image

- Confirm the backend image exposes the app on port `8808`.
- Confirm `/health` returns HTTP 200 inside the container.
- Confirm the image includes all Python dependencies from `requirements.txt`.
- Confirm the same tag is referenced in `terraform.tfvars`.

Example:

```bash
docker build -t your-registry/tour-app-backend:ec2-test ./backend
docker push your-registry/tour-app-backend:ec2-test
```

## Registry and rollout consistency

- Push both images before `terraform apply`.
- If using a private registry, make sure the EC2 instance can authenticate or pull anonymously.
- Keep frontend and backend image tags paired for each rollout.
- Record the exact image tags used for the test deployment.

## Pre-deploy smoke checks

- Run the backend image locally with `MONGODB_URL`, `DATABASE_NAME`, `SECRET_KEY`, and `FRONTEND_URL` set.
- Run the frontend image locally and open it through a reverse proxy with `/api` mapped to the backend.
- Verify login, search, and operator profile pages against the built images, not only the dev server.