provider "aws" {
  region = "us-east-1" # change to your region
}

# ==============================
# Data sources for existing infra
# ==============================
data "aws_vpc" "main" {
  id = "vpc-xxxxxxxx"
}

data "aws_subnet_ids" "private" {
  vpc_id = data.aws_vpc.main.id
}

data "aws_kms_key" "app" {
  key_id = "arn:aws:kms:us-east-1:123456789:key/xxxxxxxx"
}

# ==============================
# ECS Cluster
# ==============================
resource "aws_ecs_cluster" "app_cluster" {
  name = "nextjs-app-cluster"
}

# ==============================
# CloudWatch log group
# ==============================
resource "aws_cloudwatch_log_group" "ecs_logs" {
  name              = "/ecs/nextjs-app"
  retention_in_days = 30
}

# ==============================
# IAM roles
# ==============================
resource "aws_iam_role" "ecs_task_execution_role" {
  name = "ecsTaskExecutionRole"

  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Action = "sts:AssumeRole",
        Effect = "Allow",
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "ecs_task_execution_policy" {
  role       = aws_iam_role.ecs_task_execution_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

# ==============================
# ECS Task Definition
# ==============================
resource "aws_ecs_task_definition" "app_task" {
  family                   = "nextjs-app-task"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = "512"
  memory                   = "1024"
  execution_role_arn       = aws_iam_role.ecs_task_execution_role.arn

  container_definitions = jsonencode([
    {
      name      = "nextjs-app"
      image     = "123456789012.dkr.ecr.us-east-1.amazonaws.com/nextjs-app:latest" # your ECR image
      essential = true
      portMappings = [
        {
          containerPort = 3000
          protocol      = "tcp"
        }
      ]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          awslogs-group         = aws_cloudwatch_log_group.ecs_logs.name
          awslogs-region        = "us-east-1"
          awslogs-stream-prefix = "nextjs"
        }
      }
    }
  ])
}

# ==============================
# Security Groups
# ==============================
resource "aws_security_group" "alb_sg" {
  name        = "alb-sg"
  description = "Allow HTTPS from internal network"
  vpc_id      = data.aws_vpc.main.id

  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["10.0.0.0/16"] # adjust your internal range
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_security_group" "ecs_sg" {
  name        = "ecs-sg"
  description = "Allow traffic from ALB"
  vpc_id      = data.aws_vpc.main.id

  ingress {
    from_port       = 3000
    to_port         = 3000
    protocol        = "tcp"
    security_groups = [aws_security_group.alb_sg.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

# ==============================
# ALB + Target Group
# ==============================
resource "aws_lb" "app_alb" {
  name               = "nextjs-alb"
  internal           = true
  load_balancer_type = "application"
  subnets            = data.aws_subnet_ids.private.ids
  security_groups    = [aws_security_group.alb_sg.id]
}

resource "aws_lb_target_group" "app_tg" {
  name        = "nextjs-tg"
  port        = 3000
  protocol    = "HTTP"
  target_type = "ip"
  vpc_id      = data.aws_vpc.main.id
  health_check {
    path                = "/"
    matcher             = "200-399"
    interval            = 30
    timeout             = 5
    healthy_threshold   = 2
    unhealthy_threshold = 2
  }
}

# ==============================
# ALB Listener with Cognito Authentication
# ==============================
resource "aws_lb_listener" "https_listener" {
  load_balancer_arn = aws_lb.app_alb.arn
  port              = "443"
  protocol          = "HTTPS"
  ssl_policy        = "ELBSecurityPolicy-2016-08"
  certificate_arn   = "arn:aws:acm:us-east-1:123456789:certificate/xxxxxxxx"

  default_action {
    type = "authenticate-cognito"
    authenticate_cognito {
      user_pool_arn       = aws_cognito_user_pool.app_pool.arn
      user_pool_client_id = aws_cognito_user_pool_client.app_client.id
      user_pool_domain    = aws_cognito_user_pool_domain.app_domain.domain
      session_cookie_name = "AWSELBAuthSessionCookie"
      scope               = "email openid profile"
      session_timeout     = 3600
      on_unauthenticated_request = "authenticate"
    }

    order = 1
  }

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.app_tg.arn
    order            = 2
  }
}

# ==============================
# ECS Service
# ==============================
resource "aws_ecs_service" "app_service" {
  name            = "nextjs-app-service"
  cluster         = aws_ecs_cluster.app_cluster.id
  task_definition = aws_ecs_task_definition.app_task.arn
  launch_type     = "FARGATE"
  desired_count   = 1

  network_configuration {
    subnets         = data.aws_subnet_ids.private.ids
    security_groups = [aws_security_group.ecs_sg.id]
    assign_public_ip = false
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.app_tg.arn
    container_name   = "nextjs-app"
    container_port   = 3000
  }

  depends_on = [aws_lb_listener.https_listener]
}

# ==============================
# Cognito User Pool + SAML IdP
# ==============================
resource "aws_cognito_user_pool" "app_pool" {
  name = "nextjs-app-pool"
}

resource "aws_cognito_user_pool_domain" "app_domain" {
  domain       = "nextjs-app-auth" # change to your subdomain
  user_pool_id = aws_cognito_user_pool.app_pool.id
}

resource "aws_cognito_identity_provider" "entra_saml" {
  user_pool_id       = aws_cognito_user_pool.app_pool.id
  provider_name      = "EntraID"
  provider_type      = "SAML"
  provider_details = {
    MetadataFile       = file("entra_metadata.xml") # SAML metadata file from Entra
    IDPSignout         = "true"
    MetadataURL        = "" # optional
  }
  attribute_mapping = {
    email             = "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress"
    username          = "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/name"
    "cognito:groups"  = "http://schemas.microsoft.com/ws/2008/06/identity/claims/groups"
  }
}

resource "aws_cognito_user_pool_client" "app_client" {
  name         = "nextjs-app-client"
  user_pool_id = aws_cognito_user_pool.app_pool.id
  generate_secret = false
  allowed_oauth_flows       = ["code"]
  allowed_oauth_scopes      = ["email", "openid", "profile"]
  callback_urls             = ["https://your-alb-dns-name/"] 
  logout_urls               = ["https://your-alb-dns-name/logout"]
  supported_identity_providers = ["EntraID"]
}





# AWS region
variable "region" {
  type    = string
  default = "us-east-1"
}

# VPC and networking
variable "vpc_id" {
  type = string
}
variable "private_subnet_ids" {
  type = list(string)
}

# KMS key (if used for ECS secrets or EFS encryption)
variable "kms_key_id" {
  type = string
}

# ALB
variable "alb_certificate_arn" {
  type = string
}

# ECS
variable "ecs_cluster_name" {
  type    = string
  default = "nextjs-app-cluster"
}
variable "ecs_task_cpu" {
  type    = string
  default = "512"
}
variable "ecs_task_memory" {
  type    = string
  default = "1024"
}
variable "ecs_container_port" {
  type    = number
  default = 3000
}
variable "ecs_desired_count" {
  type    = number
  default = 1
}

# ECR image for your app
variable "ecs_container_image" {
  type = string
}

# Cognito
variable "cognito_user_pool_name" {
  type    = string
  default = "nextjs-app-pool"
}
variable "cognito_domain_prefix" {
  type    = string
  default = "nextjs-app-auth"
}
variable "cognito_saml_metadata_file" {
  type = string
}
variable "cognito_callback_urls" {
  type = list(string)
}
variable "cognito_logout_urls" {
  type = list(string)
}
variable "cognito_identity_provider_name" {
  type    = string
  default = "EntraID"
}




# ALB DNS name
output "alb_dns_name" {
  description = "Internal ALB DNS name"
  value       = aws_lb.app_alb.dns_name
}

# ECS cluster info
output "ecs_cluster_id" {
  description = "ECS Cluster ID"
  value       = aws_ecs_cluster.app_cluster.id
}

# ECS service info
output "ecs_service_arn" {
  description = "ECS Service ARN"
  value       = aws_ecs_service.app_service.arn
}

# Cognito domain
output "cognito_domain" {
  description = "Cognito domain URL"
  value       = aws_cognito_user_pool_domain.app_domain.domain
}

# Cognito user pool ID
output "cognito_user_pool_id" {
  description = "Cognito User Pool ID"
  value       = aws_cognito_user_pool.app_pool.id
}

# ECS task definition ARN
output "ecs_task_definition_arn" {
  description = "ECS Task Definition ARN"
  value       = aws_ecs_task_definition.app_task.arn
}



region                   = "us-east-1"
vpc_id                   = "vpc-0abc1234def56789"
private_subnet_ids       = ["subnet-0a1b2c3d4e5f6g7h8", "subnet-1a2b3c4d5e6f7g8h9"]
kms_key_id               = "arn:aws:kms:us-east-1:123456789:key/xxxxxxxx"
alb_certificate_arn      = "arn:aws:acm:us-east-1:123456789:certificate/xxxxxxxx"
ecs_container_image      = "123456789012.dkr.ecr.us-east-1.amazonaws.com/nextjs-app:latest"
cognito_saml_metadata_file = "entra_metadata.xml"
cognito_callback_urls    = ["https://internal-alb-dns/"]
cognito_logout_urls      = ["https://internal-alb-dns/logout"]


