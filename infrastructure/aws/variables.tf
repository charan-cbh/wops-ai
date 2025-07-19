variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "project_name" {
  description = "Project name"
  type        = string
  default     = "wops-ai"
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "production"
}

variable "snowflake_account" {
  description = "Snowflake account identifier"
  type        = string
}

variable "snowflake_user" {
  description = "Snowflake username"
  type        = string
}

variable "snowflake_warehouse" {
  description = "Snowflake warehouse name"
  type        = string
}

variable "snowflake_database" {
  description = "Snowflake database name"
  type        = string
}

variable "domain_name" {
  description = "Domain name for the application"
  type        = string
  default     = null
}

variable "certificate_arn" {
  description = "SSL certificate ARN"
  type        = string
  default     = null
}