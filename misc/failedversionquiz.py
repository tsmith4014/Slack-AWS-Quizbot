import os
import json
import boto3
import random
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from flask import Flask, request, jsonify

s3_client = boto3.client('s3')
app = App(signing_secret=os.environ.get("SLACK_SIGNING_SECRET"))
flask_app = Flask(__name__)

@app.command("/quiz")
def quiz(ack, respond, command):
    ack()
    s3_bucket = os.environ.get("S3_BUCKET")
    s3_key = os.environ.get("S3_KEY")
    response = s3_client.get_object(Bucket=s3_bucket, Key=s3_key)
    questions = json.loads(response['Body'].read().decode('utf-8'))

    selected_questions = random.sample(list(questions.items()), 10)
    user_quiz = []

    for q in selected_questions:
        question, answer = q
        user_quiz.append({
            'question': question.split("\n   ")[0],
            'options': question.split("\n   ")[1:],
            'answer': answer.split(" ")[1]
        })

    respond({
        "response_type": "in_channel",
        "text": "Starting your quiz! Answer the following questions:",
        "blocks": [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"1. {user_quiz[0]['question']}\n{user_quiz[0]['options'][0]}\n{user_quiz[0]['options'][1]}\n{user_quiz[0]['options'][2]}\n{user_quiz[0]['options'][3]}"
                }
            }
        ]
    })

@flask_app.route('/slack/events', methods=['POST'])
def slack_events():
    slack_handler = SocketModeHandler(app=app)
    slack_handler.handle(request.json)
    return jsonify(status="ok")

if __name__ == "__main__":
    flask_app.run(host='0.0.0.0', port=80)