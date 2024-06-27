#variables.tf
variable "region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "slack_signing_secret" {
  description = "Slack signing secret"
  type        = string
}

variable "slack_bot_token" {
  description = "Slack bot token"
  type        = string
}

variable "key_name" {
  description = "The name of the key pair to use for the instance"
  type        = string
}

# variable "s3_bucket" {
#   description = "S3 bucket name"
#   type        = string
# }

# variable "s3_key" {
#   description = "S3 key for the JSON file"
#   type        = string
# }

