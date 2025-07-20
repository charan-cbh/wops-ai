# DynamoDB Tables for user management

# Users table
resource "aws_dynamodb_table" "users" {
  name           = "${var.project_name}-users"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "user_id"
  stream_enabled = false

  attribute {
    name = "user_id"
    type = "S"
  }

  attribute {
    name = "email"
    type = "S"
  }

  global_secondary_index {
    name            = "email-index"
    hash_key        = "email"
    projection_type = "ALL"
  }

  tags = {
    Name = "${var.project_name}-users"
  }
}

# Email verification table
resource "aws_dynamodb_table" "email_verification" {
  name           = "${var.project_name}-email-verification"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "token"
  stream_enabled = false

  attribute {
    name = "token"
    type = "S"
  }

  attribute {
    name = "email"
    type = "S"
  }

  global_secondary_index {
    name            = "email-index"
    hash_key        = "email"
    projection_type = "ALL"
  }

  ttl {
    attribute_name = "expires_at"
    enabled        = true
  }

  tags = {
    Name = "${var.project_name}-email-verification"
  }
}

# Password reset table
resource "aws_dynamodb_table" "password_reset" {
  name           = "${var.project_name}-password-reset"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "token"
  stream_enabled = false

  attribute {
    name = "token"
    type = "S"
  }

  attribute {
    name = "email"
    type = "S"
  }

  global_secondary_index {
    name            = "email-index"
    hash_key        = "email"
    projection_type = "ALL"
  }

  ttl {
    attribute_name = "expires_at"
    enabled        = true
  }

  tags = {
    Name = "${var.project_name}-password-reset"
  }
}

# User usage table
resource "aws_dynamodb_table" "user_usage" {
  name           = "${var.project_name}-user-usage"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "user_id"
  range_key      = "date"
  stream_enabled = false

  attribute {
    name = "user_id"
    type = "S"
  }

  attribute {
    name = "date"
    type = "S"
  }

  tags = {
    Name = "${var.project_name}-user-usage"
  }
}

# Refresh tokens table
resource "aws_dynamodb_table" "refresh_tokens" {
  name           = "${var.project_name}-refresh-tokens"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "token_id"
  stream_enabled = false

  attribute {
    name = "token_id"
    type = "S"
  }

  attribute {
    name = "user_id"
    type = "S"
  }

  global_secondary_index {
    name            = "user-index"
    hash_key        = "user_id"
    projection_type = "ALL"
  }

  ttl {
    attribute_name = "expires_at"
    enabled        = true
  }

  tags = {
    Name = "${var.project_name}-refresh-tokens"
  }
}

# Messages table for chat functionality
resource "aws_dynamodb_table" "messages" {
  name           = "${var.project_name}-messages"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "message_id"
  stream_enabled = false

  attribute {
    name = "message_id"
    type = "S"
  }

  attribute {
    name = "session_id"
    type = "S"
  }

  global_secondary_index {
    name            = "session-index"
    hash_key        = "session_id"
    projection_type = "ALL"
  }

  ttl {
    attribute_name = "expires_at"
    enabled        = true
  }

  tags = {
    Name = "${var.project_name}-messages"
  }
}