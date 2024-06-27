provider "aws" {
  region = var.region
}

data "aws_caller_identity" "current" {}


resource "aws_instance" "quiz_bot_ec2" {
  ami                   = "ami-0eaf7c3456e7b5b68" # Amazon Linux 2 AMI updated and correct
  instance_type         = "t2.micro"
  key_name              = var.key_name
  vpc_security_group_ids = ["sg-04e78ea4e693c5e6f"]
  user_data = file("user_data.sh")
  tags = {
    Name = "QuizBotEC2Instance"
  }
}

output "ec2_public_dns" {
  value = aws_instance.quiz_bot_ec2.public_dns
}





# provider "aws" {
#   region = var.region
# }

# data "aws_caller_identity" "current" {}

# resource "aws_s3_bucket" "quiz_master_bucket" {
#   bucket = var.s3_bucket
# }

# resource "aws_s3_object" "quiz_json" {
#   bucket = aws_s3_bucket.quiz_master_bucket.bucket
#   key    = "lookup_table.json"
#   source = "${path.module}/../data/lookup_table.json"
# }

# resource "aws_instance" "quiz_bot_ec2" {
#   ami                   = "ami-0eaf7c3456e7b5b68" # Amazon Linux 2 AMI updated and correct
#   instance_type         = "t2.micro"
#   key_name              = "expense-app-api"
#   iam_instance_profile  = "ec2-s3-access"
#   vpc_security_group_ids = ["sg-04e78ea4e693c5e6f"]
#   user_data             = templatefile("${path.module}/../scripts/setup.sh.tpl", {
#                             slack_signing_secret = var.slack_signing_secret,
#                             slack_bot_token      = var.slack_bot_token,
#                             s3_bucket            = var.s3_bucket,
#                             s3_key               = var.s3_key
#                           })
#   tags = {
#     Name = "QuizBotEC2Instance"
#   }
# }

# output "ec2_public_dns" {
#   value = aws_instance.quiz_bot_ec2.public_dns
# }


