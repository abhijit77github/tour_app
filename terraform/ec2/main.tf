terraform {
  required_version = ">= 1.5"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

data "aws_vpc" "selected" {
  count   = var.vpc_id == null ? 1 : 0
  default = true
}

data "aws_subnets" "selected" {
  filter {
    name   = "vpc-id"
    values = [local.vpc_id]
  }
}

data "aws_ami" "ubuntu" {
  most_recent = true
  owners      = ["099720109477"]

  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd-gp3/ubuntu-noble-24.04-amd64-server-*"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

locals {
  vpc_id           = coalesce(var.vpc_id, try(data.aws_vpc.selected[0].id, null))
  subnet_id        = coalesce(var.subnet_id, try(data.aws_subnets.selected.ids[0], null))
  instance_name    = "${var.project_name}-${var.environment}-ec2"
  app_dir          = "/opt/${var.project_name}"
  mongo_url        = "mongodb://mongo:27017"
  compose_content  = templatefile("${path.module}/templates/docker-compose.yml.tftpl", {
    app_dir         = local.app_dir
    backend_image   = var.backend_image
    frontend_image  = var.frontend_image
    mongo_image     = var.mongo_image
    backend_port    = var.backend_port
    frontend_port   = var.frontend_port
    mongodb_url     = local.mongo_url
    database_name   = var.database_name
    secret_key      = var.secret_key
    frontend_origin = var.frontend_origin
    debug           = tostring(var.backend_debug)
  })
  nginx_content = templatefile("${path.module}/templates/nginx.conf.tftpl", {
    server_name      = var.domain_name
    frontend_port    = var.frontend_port
    backend_port     = var.backend_port
    client_max_body_size = var.client_max_body_size
    enable_tls       = var.enable_tls
  })
}

resource "aws_security_group" "tour_app" {
  name        = "${local.instance_name}-sg"
  description = "Security group for ${local.instance_name}"
  vpc_id      = local.vpc_id

  ingress {
    description = "HTTP"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "HTTPS"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "SSH"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = [var.ssh_ingress_cidr]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name        = "${local.instance_name}-sg"
    Environment = var.environment
    Project     = var.project_name
  }
}

resource "aws_iam_role" "tour_app" {
  name = "${local.instance_name}-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = {
        Service = "ec2.amazonaws.com"
      }
      Action = "sts:AssumeRole"
    }]
  })

  tags = {
    Name        = "${local.instance_name}-role"
    Environment = var.environment
    Project     = var.project_name
  }
}

resource "aws_iam_role_policy_attachment" "tour_app_ecr_readonly" {
  role       = aws_iam_role.tour_app.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly"
}

resource "aws_iam_instance_profile" "tour_app" {
  name = "${local.instance_name}-profile"
  role = aws_iam_role.tour_app.name
}

resource "aws_instance" "tour_app" {
  ami                         = data.aws_ami.ubuntu.id
  instance_type               = var.instance_type
  subnet_id                   = local.subnet_id
  vpc_security_group_ids      = [aws_security_group.tour_app.id]
  key_name                    = var.key_name
  iam_instance_profile        = aws_iam_instance_profile.tour_app.name
  associate_public_ip_address = true

  root_block_device {
    volume_size = var.root_volume_size
    volume_type = "gp3"
  }

  user_data = templatefile("${path.module}/templates/user_data.sh.tftpl", {
    app_dir          = local.app_dir
    compose_content  = base64encode(local.compose_content)
    nginx_content    = base64encode(local.nginx_content)
    aws_region       = var.aws_region
    backend_image    = var.backend_image
    frontend_image   = var.frontend_image
    enable_tls       = var.enable_tls
    tls_email        = var.tls_email
    domain_name      = var.domain_name
  })
  user_data_replace_on_change = true

  tags = {
    Name        = local.instance_name
    Environment = var.environment
    Project     = var.project_name
  }
}

resource "aws_eip" "tour_app" {
  count    = var.allocate_eip ? 1 : 0
  domain   = "vpc"
  instance = aws_instance.tour_app.id

  tags = {
    Name        = "${local.instance_name}-eip"
    Environment = var.environment
    Project     = var.project_name
  }
}