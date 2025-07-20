# ECS Task Execution Role
resource "aws_iam_role" "ecs_execution" {
  name = "${var.project_name}-ecs-execution-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "ecs_execution" {
  role       = aws_iam_role.ecs_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

# ECS Task Role
resource "aws_iam_role" "ecs_task" {
  name = "${var.project_name}-ecs-task-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        }
      }
    ]
  })
}

# S3 Access Policy for ECS Task
resource "aws_iam_policy" "ecs_s3_access" {
  name        = "${var.project_name}-ecs-s3-access"
  description = "IAM policy for ECS tasks to access S3"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject"
        ]
        Resource = "${aws_s3_bucket.files.arn}/*"
      },
      {
        Effect = "Allow"
        Action = [
          "s3:ListBucket"
        ]
        Resource = aws_s3_bucket.files.arn
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "ecs_s3_access" {
  role       = aws_iam_role.ecs_task.name
  policy_arn = aws_iam_policy.ecs_s3_access.arn
}

# Secrets Manager Access Policy
resource "aws_iam_policy" "ecs_secrets_access" {
  name        = "${var.project_name}-ecs-secrets-access"
  description = "IAM policy for ECS tasks to access Secrets Manager"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue"
        ]
        Resource = [
          aws_secretsmanager_secret.openai_key.arn,
          aws_secretsmanager_secret.anthropic_key.arn,
          aws_secretsmanager_secret.google_key.arn,
          aws_secretsmanager_secret.snowflake_private_key.arn,
          aws_secretsmanager_secret.snowflake_private_key_passphrase.arn,
          aws_secretsmanager_secret.jwt_secret.arn,
          aws_secretsmanager_secret.db_password.arn
        ]
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "ecs_secrets_access_task" {
  role       = aws_iam_role.ecs_task.name
  policy_arn = aws_iam_policy.ecs_secrets_access.arn
}

resource "aws_iam_role_policy_attachment" "ecs_secrets_access_execution" {
  role       = aws_iam_role.ecs_execution.name
  policy_arn = aws_iam_policy.ecs_secrets_access.arn
}

# DynamoDB Access Policy for ECS Task
resource "aws_iam_policy" "ecs_dynamodb_access" {
  name        = "${var.project_name}-ecs-dynamodb-access"
  description = "IAM policy for ECS tasks to access DynamoDB"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "dynamodb:PutItem",
          "dynamodb:GetItem",
          "dynamodb:UpdateItem",
          "dynamodb:DeleteItem",
          "dynamodb:Query",
          "dynamodb:Scan"
        ]
        Resource = [
          aws_dynamodb_table.users.arn,
          aws_dynamodb_table.email_verification.arn,
          aws_dynamodb_table.password_reset.arn,
          aws_dynamodb_table.user_usage.arn,
          aws_dynamodb_table.refresh_tokens.arn,
          aws_dynamodb_table.messages.arn,
          "${aws_dynamodb_table.users.arn}/index/*",
          "${aws_dynamodb_table.email_verification.arn}/index/*",
          "${aws_dynamodb_table.password_reset.arn}/index/*",
          "${aws_dynamodb_table.user_usage.arn}/index/*",
          "${aws_dynamodb_table.refresh_tokens.arn}/index/*",
          "${aws_dynamodb_table.messages.arn}/index/*"
        ]
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "ecs_dynamodb_access" {
  role       = aws_iam_role.ecs_task.name
  policy_arn = aws_iam_policy.ecs_dynamodb_access.arn
}

# SES Access Policy for ECS Task
resource "aws_iam_policy" "ecs_ses_access" {
  name        = "${var.project_name}-ecs-ses-access"
  description = "IAM policy for ECS tasks to access SES"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "ses:SendEmail",
          "ses:SendRawEmail"
        ]
        Resource = "*"
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "ecs_ses_access" {
  role       = aws_iam_role.ecs_task.name
  policy_arn = aws_iam_policy.ecs_ses_access.arn
}