provider "aws" {
  region = "us-east-1"
}

data "aws_caller_identity" "current" {}

resource "aws_s3_bucket" "quiz_master_bucket" {
  bucket = var.s3_bucket
}

resource "aws_s3_object" "quiz_json" {
  bucket = aws_s3_bucket.quiz_master_bucket.bucket
  key    = "lookup_table.json"
  source = "${path.module}/../data/lookup_table.json"
}

resource "aws_instance" "quiz_bot_ec2" {
  ami           = "ami-0c55b159cbfafe1f0" # Amazon Linux 2 AMI (adjust as needed)
  instance_type = "t2.micro"
  key_name      = "your-key-pair"
  user_data     = file("${path.module}/../scripts/setup.sh")
  tags = {
    Name = "QuizBotEC2Instance"
  }
}

output "ec2_public_dns" {
  value = aws_instance.quiz_bot_ec2.public_dns
}

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
  default     = "quiz-master-bucket"
}

variable "region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}





# provider "aws" {
#   region = "us-east-1"
# }

# data "aws_caller_identity" "current" {}

# resource "aws_s3_bucket" "quiz_master_bucket" {
#   bucket = var.s3_bucket
#   # Do not set any ACL or object_ownership here
# }

# resource "aws_lambda_function" "slack_quiz_bot" {
#   function_name = "slack_quiz_bot"
#   handler       = "lambda_function.handler"
#   runtime       = "python3.8"
#   role          = aws_iam_role.lambda_exec.arn
#   filename      = "${path.module}/../lambda.zip"
#   environment {
#     variables = {
#       SLACK_SIGNING_SECRET = var.slack_signing_secret
#       SLACK_BOT_TOKEN      = var.slack_bot_token
#       S3_BUCKET            = var.s3_bucket
#       S3_KEY               = var.s3_key
#     }
#   }
# }

# resource "aws_iam_role" "lambda_exec" {
#   name = "lambda_exec_role_quiz_bot"
#   assume_role_policy = jsonencode({
#     Version = "2012-10-17"
#     Statement = [
#       {
#         Action = "sts:AssumeRole"
#         Effect = "Allow"
#         Principal = {
#           Service = "lambda.amazonaws.com"
#         }
#       }
#     ]
#   })
# }

# resource "aws_iam_role_policy_attachment" "lambda_basic_execution" {
#   role       = aws_iam_role.lambda_exec.name
#   policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
# }

# resource "aws_cloudwatch_log_group" "lambda_log_group" {
#   name              = "/aws/lambda/${aws_lambda_function.slack_quiz_bot.function_name}"
#   retention_in_days = 14
# }

# resource "aws_api_gateway_rest_api" "api" {
#   name        = "Slack Quiz Bot API"
#   description = "API Gateway for the Slack Quiz Bot"
# }

# resource "aws_api_gateway_resource" "slack_command" {
#   rest_api_id = aws_api_gateway_rest_api.api.id
#   parent_id   = aws_api_gateway_rest_api.api.root_resource_id
#   path_part   = "slack"
# }

# resource "aws_api_gateway_method" "post_slack_command" {
#   rest_api_id   = aws_api_gateway_rest_api.api.id
#   resource_id   = aws_api_gateway_resource.slack_command.id
#   http_method   = "POST"
#   authorization = "NONE"
# }

# resource "aws_api_gateway_integration" "lambda" {
#   rest_api_id             = aws_api_gateway_rest_api.api.id
#   resource_id             = aws_api_gateway_resource.slack_command.id
#   http_method             = aws_api_gateway_method.post_slack_command.http_method
#   integration_http_method = "POST"
#   type                    = "AWS_PROXY"
#   uri                     = "arn:aws:apigateway:${var.region}:lambda:path/2015-03-31/functions/${aws_lambda_function.slack_quiz_bot.arn}/invocations"
# }

# resource "aws_api_gateway_deployment" "api_deployment" {
#   rest_api_id = aws_api_gateway_rest_api.api.id
#   stage_name  = "prod"
#   depends_on = [
#     aws_api_gateway_integration.lambda
#   ]

#   lifecycle {
#     create_before_destroy = true
#   }
# }

# resource "aws_lambda_permission" "api_gateway" {
#   statement_id  = "AllowAPIGatewayInvoke"
#   action        = "lambda:InvokeFunction"
#   function_name = aws_lambda_function.slack_quiz_bot.function_name
#   principal     = "apigateway.amazonaws.com"
#   source_arn    = "arn:aws:execute-api:${var.region}:${data.aws_caller_identity.current.account_id}:${aws_api_gateway_rest_api.api.id}/*/POST/slack"
# }