# EC2 Deployment Execution Log

Date: 2026-06-14

Goal: deploy the application to a single EC2 instance behind Nginx using Terraform, with AWS profile `admin`.

## Execution checklist

- [x] Confirm AWS profile access with STS
- [x] Select deployment region and inspect default networking
- [x] Check Docker access for image build/push
- [x] Install or stage a Terraform binary locally
- [x] Create or confirm ECR repositories for backend and frontend images
- [x] Build backend image
- [x] Build frontend image with `VITE_API_URL=/api`
- [x] Push backend image to ECR
- [x] Push frontend image to ECR
- [x] Prepare `terraform/ec2/terraform.tfvars`
- [x] Run `terraform init`
- [x] Run `terraform plan`
- [x] Run `terraform apply`
- [x] Capture outputs: instance IP, URL, SSH command
- [x] Post-deploy smoke checks on EC2 stack

## Findings so far

- AWS profile `admin` is valid for account `687654644864`.
- Candidate region selected: `ap-south-1`.
- Default VPC exists in `ap-south-1`: `vpc-ebfa9383`.
- Available default VPC subnets discovered: `subnet-c0eb12bb`, `subnet-6215df2e`, `subnet-0a731662`.
- Existing EC2 key pair discovered in `ap-south-1`: `aimlaws`.
- Docker daemon access works through `sudo -n docker`.
- Terraform is not preinstalled in the current environment, so a local binary was staged before running the stack.
- The original EC2 bootstrap failed because shell variable interpolation in `user_data.sh.tftpl` conflicted with Terraform templating.
- The first EC2 rollout returned `502` because host Nginx was proxying to ports that were only `expose`d inside Docker, not published to the host.
- The second EC2 rollout failed to pull private ECR images because the instance had no IAM-backed ECR read access.
- The third EC2 rollout failed because the selected Ubuntu 24.04 AMI did not provide an installable `awscli` apt package.
- The fourth EC2 rollout reached Docker successfully, but the backend image had Python dependencies installed into root's user site while the container ran as `appuser`, which broke imports in the seed container.
- After fixing the backend image, the live host recovered successfully by pulling the corrected image and recreating the compose services over SSH.

## Planned concrete deployment inputs

- Region: `ap-south-1`
- Instance type: `t3.medium`
- Key pair: `aimlaws`
- Database name: `tour_app_db`
- Frontend API base at build time: `/api`
- Public entrypoint: EC2 public IP first, domain/TLS later if desired

## Concrete resources created

- EC2 instance: `i-057e391ef6d2f249a`
- Elastic IP: `13.206.60.201`
- Public URL: `http://13.206.60.201`
- Public DNS: `ec2-13-205-16-146.ap-south-1.compute.amazonaws.com`
- SSH command: `ssh ubuntu@13.206.60.201`
- Security group: `sg-017dd93dc04bbed23`
- IAM instance profile: `tour-app-staging-ec2-profile`

## Final verification

- `http://13.206.60.201/api/health` returned `200` with `{"status":"healthy"}`.
- `http://13.206.60.201/` returned the frontend `index.html` for the Tour App.
- The backend container reported `healthy` on the instance.
- The frontend container reported `healthy` on the instance and is reachable through Nginx.
- The seed container completed successfully and created local demo users, admins, operator profiles, bookings, and ratings.

## Notes

- This log is updated as execution progresses.
- The EC2 Terraform stack lives under `terraform/ec2/`.
- The EC2 path assumes Docker images are available in ECR before `terraform apply`.