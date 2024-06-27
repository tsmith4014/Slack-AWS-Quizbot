provider "aws" {
  region = var.region
}

data "aws_caller_identity" "current" {}

resource "aws_instance" "quiz_bot_ec2" {
  ami                   = "ami-0eaf7c3456e7b5b68" # Amazon Linux 2 AMI
  instance_type         = "t2.micro"
  key_name              = var.key_name
  vpc_security_group_ids = [aws_security_group.quiz_bot_sg.id]
  user_data             = file("user_data.sh")
  
  tags = {
    Name = "QuizBotEC2Instance"
  }
}

resource "aws_security_group" "quiz_bot_sg" {
  name_prefix = "quiz_bot_sg"

  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

output "ec2_public_dns" {
  value = aws_instance.quiz_bot_ec2.public_dns
}