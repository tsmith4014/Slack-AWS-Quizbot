# Flask Quiz Bot Deployment on AWS EC2 with Terraform

This guide will help you deploy a Flask quiz bot on an AWS EC2 instance using Terraform. The setup includes Nginx as a reverse proxy and installs all necessary dependencies.

## File Tree

```
/flask_app
  ├── main.tf
  ├── variables.tf
  ├── terraform.tfvars
  ├── user_data.sh
  ├── app.py
  └── lookup_table.json
```

## Prerequisites

- AWS account
- Terraform installed on your local machine
- AWS CLI configured with appropriate credentials
- SSH key pair created in the AWS region you are using

## Step-by-Step Guide

### 1. Create `main.tf`

This file defines the main configuration for Terraform to provision the AWS resources.

```hcl
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
```

### 2. Create `variables.tf`

This file defines the variables used in the Terraform configuration.

```hcl
variable "region" {
  description = "AWS region"
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
```

### 3. Create `terraform.tfvars`

This file contains the actual values for the variables. Replace the placeholder values with your actual data.

```hcl
region               = "us-east-1" # Update if you use a different region
slack_signing_secret = "your-slack-signing-secret"
slack_bot_token      = "your-slack-bot-token"
key_name             = "your-key-pair-name"
```

### 4. Create `user_data.sh`

This script will be used to configure the EC2 instance, install necessary packages, and deploy the Flask app.

```bash
#!/bin/bash
yum update -y
yum install -y python3 python3-pip nginx git

# Install Flask
pip3 install flask

# Install Slack dependencies
pip3 install slack_sdk

# Set environment variables
export SLACK_SIGNING_SECRET="${slack_signing_secret}"
export SLACK_BOT_TOKEN="${slack_bot_token}"

# Create application directory
mkdir -p /home/ec2-user/flask_app
cd /home/ec2-user/flask_app

# Write the Flask app
cat << 'EOF' > app.py
from flask import Flask, request, jsonify
import json
import random

app = Flask(__name__)

# Function to load the lookup table from a JSON file
def load_lookup_table(file_path):
    with open(file_path, 'r') as file:
        return json.load(file)

# Load the lookup table
lookup_table = load_lookup_table('/home/ec2-user/flask_app/lookup_table.json')  # Update with the correct file path

# Route to start a quiz
@app.route('/start_quiz', methods=['POST'])
def start_quiz():
    data = request.json
    num_questions = data.get('num_questions', 5)
    questions = list(lookup_table.keys())
    question_counter = 1
    score = 0
    quiz_results = []

    for _ in range(num_questions):
        question = random.choice(questions)
        quiz_results.append({
            "question_number": question_counter,
            "question": question.split('. ', 1)[1],
            "correct_answer": lookup_table[question].split('. ', 1)[1]
        })
        question_counter += 1

    return jsonify({
        "quiz_results": quiz_results,
        "num_questions": num_questions
    })

# Route to evaluate answers
@app.route('/evaluate_answers', methods=['POST'])
def evaluate_answers():
    data = request.json
    user_answers = data.get('user_answers', [])
    score = 0

    for user_answer in user_answers:
        question = user_answer.get('question')
        user_response = user_answer.get('answer').strip()

        correct_answer = lookup_table[question].split('. ')[0]
        user_answers_set = set([answer.strip() for answer in user_response.split(',')])
        correct_answers_set = set([answer.strip() for answer in correct_answer.split(',')])

        if user_answers_set == correct_answers_set:
            score += 1

    return jsonify({
        "score": score,
        "total_questions": len(user_answers)
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0')
EOF

# Create systemd service
cat << 'EOF' > /etc/systemd/system/flask_app.service
[Unit]
Description=Flask Application

[Service]
User=ec2-user
WorkingDirectory=/home/ec2-user/flask_app
Environment="SLACK_SIGNING_SECRET=${slack_signing_secret}"
Environment="SLACK_BOT_TOKEN=${slack_bot_token}"
ExecStart=/usr/bin/python3 /home/ec2-user/flask_app/app.py

[Install]
WantedBy=multi-user.target
EOF

# Enable and start the Flask app service
systemctl daemon-reload
systemctl enable flask_app.service
systemctl start flask_app.service

# Configure Nginx
cat << 'EOF' > /etc/nginx/conf.d/flask_app.conf
server {
    listen 80;
    server_name _;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
EOF

# Restart Nginx
systemctl enable nginx
systemctl restart nginx
```

### 5. Create `app.py`

This is your Flask application.

````python
from flask import Flask, request, jsonify
import json
import random

app = Flask(__name__)

# Function to load the lookup table from a JSON file
def load_lookup_table(file_path):
    with open(file_path, 'r') as file:
        return json.load(file)

# Load the lookup table
lookup_table = load_lookup_table('/home/ec2-user/flask_app/lookup_table.json')  # Update with the correct file path

# Route to start a quiz
@app.route('/start_quiz', methods=['POST'])
def start_quiz():
    data = request.json
    num_questions = data.get('num_questions', 5)
    questions = list(lookup_table.keys())
    question_counter = 1
    score = 0
    quiz_results = []

    for _ in range(num_questions):
        question = random.choice(questions)
        quiz_results.append({
            "question_number": question_counter,
            "question": question.split('. ', 1)[1],
            "correct_answer": lookup_table[question].split('. ', 1)[1]
        })
        question_counter += 1

    return jsonify({
        "quiz_results": quiz_results,
        "num_questions": num_questions
    })

# Route to evaluate answers
@app.route('/evaluate_answers', methods=['POST'])
def evaluate_answers():
    data = request.json
    user_answers = data.get('user_answers', [])
    score = 0

    for user_answer in user_answers:
        question = user_answer.get('question')
        user_response = user_answer.get('answer').strip()

        correct_answer = lookup_table[question].split('. ')[0]
        user_answers_set = set([answer.strip() for answer in user_response.split(',')])
        correct_answers_set = set([answer.strip() for answer in correct_answer.split(',')])

        if user_answers_set == correct_answers_set:
            score += 1

    return jsonify({
        "score": score,
        "total_questions": len(user_answers)
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0')


### Deployment Steps

1. **Initialize Terraform:**

```bash
terraform init
````

2. **Plan the deployment:**

```bash
terraform plan
```

3. **Apply the deployment:**

```bash
terraform apply
```

4. **Access the Flask App:**

After Terraform completes the deployment, you can find the public DNS of your EC2 instance in the output. Open your browser and navigate to `http://<ec2_public_dns>` to access your Flask app.

### Important Notes

- Replace placeholder values in `terraform.tfvars` with your actual Slack signing secret, Slack bot token, and key pair name.
- Ensure the `lookup_table.json` file is correctly referenced and contains the appropriate data for your quiz.
- Make sure the security group allows traffic on port 80 (HTTP) to access the web application.

---
