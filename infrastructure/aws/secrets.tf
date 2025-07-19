# Secrets Manager
resource "aws_secretsmanager_secret" "openai_key" {
  name                    = "${var.project_name}-openai-key"
  description            = "OpenAI API Key"
  recovery_window_in_days = 7
}

resource "aws_secretsmanager_secret" "anthropic_key" {
  name                    = "${var.project_name}-anthropic-key"
  description            = "Anthropic API Key"
  recovery_window_in_days = 7
}

resource "aws_secretsmanager_secret" "google_key" {
  name                    = "${var.project_name}-google-key"
  description            = "Google API Key"
  recovery_window_in_days = 7
}

resource "aws_secretsmanager_secret" "snowflake_password" {
  name                    = "${var.project_name}-snowflake-password"
  description            = "Snowflake Password"
  recovery_window_in_days = 7
}

# You'll need to manually set these secret values after deployment
resource "aws_secretsmanager_secret_version" "openai_key_placeholder" {
  secret_id     = aws_secretsmanager_secret.openai_key.id
  secret_string = "REPLACE_WITH_ACTUAL_KEY"
  
  lifecycle {
    ignore_changes = [secret_string]
  }
}

resource "aws_secretsmanager_secret_version" "anthropic_key_placeholder" {
  secret_id     = aws_secretsmanager_secret.anthropic_key.id
  secret_string = "REPLACE_WITH_ACTUAL_KEY"
  
  lifecycle {
    ignore_changes = [secret_string]
  }
}

resource "aws_secretsmanager_secret_version" "google_key_placeholder" {
  secret_id     = aws_secretsmanager_secret.google_key.id
  secret_string = "REPLACE_WITH_ACTUAL_KEY"
  
  lifecycle {
    ignore_changes = [secret_string]
  }
}

resource "aws_secretsmanager_secret_version" "snowflake_password_placeholder" {
  secret_id     = aws_secretsmanager_secret.snowflake_password.id
  secret_string = "REPLACE_WITH_ACTUAL_PASSWORD"
  
  lifecycle {
    ignore_changes = [secret_string]
  }
}