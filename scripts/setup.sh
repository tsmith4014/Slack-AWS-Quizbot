#!/bin/bash
# Update and install dependencies
echo "Updating and installing dependencies..."
sudo yum update -y
sudo yum install -y python3 git

# Install pip and Python dependencies
echo "Installing pip and Python dependencies..."
sudo pip3 install boto3 slack_bolt flask

# Clone the repository and navigate to the project directory
REPO_DIR="/home/ec2-user/Slack-AWS-Quizbot"
echo "Cloning the repository..."
if [ -d "$REPO_DIR" ]; then
  echo "Directory $REPO_DIR already exists. Pulling latest changes."
  cd "$REPO_DIR"
  git pull
else
  git clone https://github.com/tsmith4014/Slack-AWS-Quizbot "$REPO_DIR"
  if [ $? -ne 0 ]; then
      echo "Failed to clone the repository."
      exit 1
  fi
  cd "$REPO_DIR"
fi

# Create environment variables from Terraform variables
echo "Setting environment variables..."
echo "export SLACK_SIGNING_SECRET=${slack_signing_secret}" >> /home/ec2-user/.bashrc
echo "export SLACK_BOT_TOKEN=${slack_bot_token}" >> /home/ec2-user/.bashrc
echo "export S3_BUCKET=${s3_bucket}" >> /home/ec2-user/.bashrc
echo "export S3_KEY=${s3_key}" >> /home/ec2-user/.bashrc

# Reload bashrc to apply environment variables
source /home/ec2-user/.bashrc

# Verify environment variables
echo "Verifying environment variables..."
echo "SLACK_SIGNING_SECRET=$SLACK_SIGNING_SECRET"
echo "SLACK_BOT_TOKEN=$SLACK_BOT_TOKEN"
echo "S3_BUCKET=$S3_BUCKET"
echo "S3_KEY=$S3_KEY"

# Debug: Check environment variables
env | grep SLACK
env | grep S3

# Start the Flask app
echo "Starting the Flask app..."
python3 quiz.py &
if [ $? -ne 0 ]; then
    echo "Failed to start the Flask app."
    exit 1
fi

echo "Setup script completed successfully."