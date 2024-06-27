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
lookup_table = load_lookup_table('lookup_table.json')  # Update with the correct file path

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