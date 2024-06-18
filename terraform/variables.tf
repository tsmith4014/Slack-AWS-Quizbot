#variables.tf
variable "slack_signing_secret" {
  description = "Slack signing secret"
  type        = string
}

variable "slack_bot_token" {
  description = "Slack bot token"
  type        = string
}

variable "s3_bucket" {
  description = "S3 bucket name"
  type        = string
}

variable "s3_key" {
  description = "S3 key for the JSON file"
  type        = string
}

variable "region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}