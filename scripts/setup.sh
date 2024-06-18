#!/bin/bash
# Update and install dependencies
sudo yum update -y
sudo yum install -y python3 git

# Install pip and Python dependencies
sudo pip3 install boto3 slack_bolt flask

# Clone the repository and navigate to the project directory
git clone https://github.com/your-repo/Slack-AWS-Quizbot.git /home/ec2-user/Slack-AWS-Quizbot
cd /home/ec2-user/Slack-AWS-Quizbot

# Create environment variables from Terraform variables
echo "export SLACK_SIGNING_SECRET=${slack_signing_secret}" >> /home/ec2-user/.bashrc
echo "export SLACK_BOT_TOKEN=${slack_bot_token}" >> /home/ec2-user/.bashrc
echo "export S3_BUCKET=${s3_bucket}" >> /home/ec2-user/.bashrc
echo "export S3_KEY=lookup_table.json" >> /home/ec2-user/.bashrc

# Reload bashrc to apply environment variables
source /home/ec2-user/.bashrc

# Start the Flask app
python3 quiz.py &