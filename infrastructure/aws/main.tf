terraform {
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

# VPC
resource "aws_vpc" "main" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = {
    Name = "${var.project_name}-vpc"
  }
}

# Internet Gateway
resource "aws_internet_gateway" "main" {
  vpc_id = aws_vpc.main.id

  tags = {
    Name = "${var.project_name}-igw"
  }
}

# Subnets
resource "aws_subnet" "public" {
  count = 2

  vpc_id                  = aws_vpc.main.id
  cidr_block              = "10.0.${count.index + 1}.0/24"
  availability_zone       = data.aws_availability_zones.available.names[count.index]
  map_public_ip_on_launch = true

  tags = {
    Name = "${var.project_name}-public-subnet-${count.index + 1}"
  }
}

resource "aws_subnet" "private" {
  count = 2

  vpc_id            = aws_vpc.main.id
  cidr_block        = "10.0.${count.index + 10}.0/24"
  availability_zone = data.aws_availability_zones.available.names[count.index]

  tags = {
    Name = "${var.project_name}-private-subnet-${count.index + 1}"
  }
}

# Route Tables
resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.main.id
  }

  tags = {
    Name = "${var.project_name}-public-rt"
  }
}

resource "aws_route_table_association" "public" {
  count = length(aws_subnet.public)

  subnet_id      = aws_subnet.public[count.index].id
  route_table_id = aws_route_table.public.id
}

# Security Groups
resource "aws_security_group" "alb" {
  name_prefix = "${var.project_name}-alb-"
  vpc_id      = aws_vpc.main.id

  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    from_port   = 8000
    to_port     = 8000
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.project_name}-alb-sg"
  }
}

resource "aws_security_group" "ecs" {
  name_prefix = "${var.project_name}-ecs-"
  vpc_id      = aws_vpc.main.id

  ingress {
    from_port       = 0
    to_port         = 65535
    protocol        = "tcp"
    security_groups = [aws_security_group.alb.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.project_name}-ecs-sg"
  }
}

# ECS Cluster
resource "aws_ecs_cluster" "main" {
  name = "${var.project_name}-cluster"

  setting {
    name  = "containerInsights"
    value = "enabled"
  }
}

# ECS Task Definition
resource "aws_ecs_task_definition" "backend" {
  family                   = "${var.project_name}-backend"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = 512
  memory                   = 1024
  execution_role_arn       = aws_iam_role.ecs_execution.arn
  task_role_arn           = aws_iam_role.ecs_task.arn

  container_definitions = jsonencode([
    {
      name  = "backend"
      image = var.backend_image_uri
      
      portMappings = [
        {
          containerPort = 8000
          protocol      = "tcp"
        }
      ]

      environment = [
        {
          name  = "ENVIRONMENT"
          value = "production"
        },
        {
          name  = "USE_LOCAL_DB"
          value = "false"
        },
        {
          name  = "USE_LOCAL_EMAIL"
          value = "false"
        },
        {
          name  = "USE_LOCAL_STORAGE"
          value = "false"
        },
        {
          name  = "DEBUG"
          value = "false"
        },
        {
          name  = "APP_NAME"
          value = "Worker Operations BI Chatbot"
        },
        {
          name  = "VERSION"
          value = "1.0.0"
        },
        {
          name  = "ACCESS_TOKEN_EXPIRE_MINUTES"
          value = "30"
        },
        {
          name  = "REFRESH_TOKEN_EXPIRE_DAYS"
          value = "7"
        },
        {
          name  = "FRONTEND_URL"
          value = "https://${aws_lb.main.dns_name}"
        },
        {
          name  = "DEFAULT_AI_PROVIDER"
          value = "openai"
        },
        {
          name  = "USERS_TABLE"
          value = aws_dynamodb_table.users.name
        },
        {
          name  = "AWS_REGION"
          value = var.aws_region
        },
        {
          name  = "EMAIL_BACKEND"
          value = "ses"
        },
        {
          name  = "SES_SENDER_EMAIL"
          value = "noreply@clipboardhealth.com"
        },
        {
          name  = "ALLOWED_EMAIL_DOMAINS"
          value = "clipboardhealth.com"
        },
        {
          name  = "VERIFICATION_EXPIRY_HOURS"
          value = "24"
        },
        {
          name  = "PASSWORD_RESET_EXPIRY_HOURS"
          value = "1"
        },
        {
          name  = "MAX_FILE_SIZE"
          value = "10485760"
        },
        {
          name  = "ALLOWED_FILE_TYPES"
          value = ".pdf,.txt,.csv,.json,.xlsx"
        },
        {
          name  = "S3_BUCKET_NAME"
          value = aws_s3_bucket.files.bucket
        },
        {
          name  = "SNOWFLAKE_ACCOUNT"
          value = var.snowflake_account
        },
        {
          name  = "SNOWFLAKE_USER"
          value = var.snowflake_user
        },
        {
          name  = "SNOWFLAKE_WAREHOUSE"
          value = var.snowflake_warehouse
        },
        {
          name  = "SNOWFLAKE_DATABASE"
          value = var.snowflake_database
        },
        {
          name  = "SNOWFLAKE_SCHEMA"
          value = var.snowflake_schema
        },
        {
          name  = "OPENAI_ASSISTANT_ID"
          value = "asst_gdVxdkcSfEE1I7bpkXChUUuY"
        },
        {
          name  = "VERIFICATION_TABLE"
          value = aws_dynamodb_table.email_verification.name
        },
        {
          name  = "PASSWORD_RESET_TABLE"
          value = aws_dynamodb_table.password_reset.name
        },
        {
          name  = "USAGE_TABLE"
          value = aws_dynamodb_table.user_usage.name
        },
        {
          name  = "TOKENS_TABLE"
          value = "wops-refresh-tokens"
        },
        {
          name  = "ADMIN_EMAIL"
          value = "admin@clipboardhealth.com"
        },
        {
          name  = "ADMIN_PASSWORD"
          value = "admin123"
        },
        {
          name  = "CHAT_STORAGE_TYPE"
          value = "dynamodb"
        },
        {
          name  = "DYNAMODB_MESSAGES_TABLE"
          value = aws_dynamodb_table.messages.name
        }
      ]

      secrets = [
        {
          name      = "OPENAI_API_KEY"
          valueFrom = aws_secretsmanager_secret.openai_key.arn
        },
        {
          name      = "ANTHROPIC_API_KEY"
          valueFrom = aws_secretsmanager_secret.anthropic_key.arn
        },
        {
          name      = "GOOGLE_API_KEY"
          valueFrom = aws_secretsmanager_secret.google_key.arn
        },
        {
          name      = "SNOWFLAKE_PRIVATE_KEY"
          valueFrom = aws_secretsmanager_secret.snowflake_private_key.arn
        },
        {
          name      = "SNOWFLAKE_PRIVATE_KEY_PASSPHRASE"
          valueFrom = aws_secretsmanager_secret.snowflake_private_key_passphrase.arn
        },
        {
          name      = "JWT_SECRET_KEY"
          valueFrom = aws_secretsmanager_secret.jwt_secret.arn
        }
      ]

      logConfiguration = {
        logDriver = "awslogs"
        options = {
          awslogs-group         = aws_cloudwatch_log_group.backend.name
          awslogs-region        = var.aws_region
          awslogs-stream-prefix = "ecs"
        }
      }

      healthCheck = {
        command     = ["CMD-SHELL", "python -c \"import urllib.request; urllib.request.urlopen('http://localhost:8000/health')\" || exit 1"]
        interval    = 30
        timeout     = 5
        retries     = 3
        startPeriod = 60
      }
    }
  ])
}

resource "aws_ecs_task_definition" "frontend" {
  family                   = "${var.project_name}-frontend"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = 256
  memory                   = 512
  execution_role_arn       = aws_iam_role.ecs_execution.arn

  container_definitions = jsonencode([
    {
      name  = "frontend"
      image = var.frontend_image_uri
      
      portMappings = [
        {
          containerPort = 3000
          protocol      = "tcp"
        }
      ]

      environment = [
        {
          name  = "NEXT_PUBLIC_API_URL"
          value = "https://${aws_lb.main.dns_name}"
        }
      ]

      logConfiguration = {
        logDriver = "awslogs"
        options = {
          awslogs-group         = aws_cloudwatch_log_group.frontend.name
          awslogs-region        = var.aws_region
          awslogs-stream-prefix = "ecs"
        }
      }
    }
  ])
}

# ECS Services
resource "aws_ecs_service" "backend" {
  name            = "${var.project_name}-backend"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.backend.arn
  desired_count   = 2
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = aws_subnet.public[*].id
    security_groups  = [aws_security_group.ecs.id]
    assign_public_ip = true
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.backend.arn
    container_name   = "backend"
    container_port   = 8000
  }

  depends_on = [aws_lb_listener.backend]
}

resource "aws_ecs_service" "frontend" {
  name            = "${var.project_name}-frontend"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.frontend.arn
  desired_count   = 2
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = aws_subnet.public[*].id
    security_groups  = [aws_security_group.ecs.id]
    assign_public_ip = true
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.frontend.arn
    container_name   = "frontend"
    container_port   = 3000
  }

  depends_on = [aws_lb_listener.main]
}

# Data sources
data "aws_availability_zones" "available" {
  state = "available"
}