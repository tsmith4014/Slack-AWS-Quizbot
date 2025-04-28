#app.py
from flask import Flask, request, jsonify
import json
import random
import hmac
import hashlib
import time
import os
import logging
from uuid import uuid4
import requests

app = Flask(__name__)

SLACK_SIGNING_SECRET = os.environ['SLACK_SIGNING_SECRET']
SLACK_BOT_TOKEN = os.environ['SLACK_BOT_TOKEN']
quiz_sessions = {}

def verify_slack_request(data, timestamp, signature):
    req = str.encode('v0:' + str(timestamp) + ':') + data
    request_hash = 'v0=' + hmac.new(
        str.encode(SLACK_SIGNING_SECRET),
        req, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(request_hash, signature)

def load_lookup_table(file_path):
    with open(file_path, 'r') as file:
        return json.load(file)

lookup_table = load_lookup_table('../lookup_table.json')

@app.route('/start_quiz', methods=['POST'])
def start_quiz():
    app.logger.info("start_quiz endpoint called")
    if 'X-Slack-Request-Timestamp' not in request.headers or 'X-Slack-Signature' not in request.headers:
        app.logger.error("Missing headers")
        return jsonify({"error": "Unauthorized"}), 403

    timestamp = request.headers['X-Slack-Request-Timestamp']
    signature = request.headers['X-Slack-Signature']
    
    if abs(time.time() - int(timestamp)) > 60 * 5:
        app.logger.error("Request timestamp too old")
        return jsonify({"error": "Unauthorized"}), 403

    if not verify_slack_request(request.get_data(), timestamp, signature):
        app.logger.error("Slack request verification failed")
        return jsonify({"error": "Unauthorized"}), 403

    try:
        data = request.form
        app.logger.info(f"Form data: {data}")
        num_questions = int(data.get('text', 5))
        user_id = data.get('user_id')
        questions = list(lookup_table.keys())
        session_id = str(uuid4())
        quiz_sessions[user_id] = {
            "questions": random.sample(questions, num_questions),
            "current_question": 0,
            "score": 0,
            "num_questions": num_questions,
            "selected_answers": []
        }

        current_question = quiz_sessions[user_id]["questions"][0]
        question_parts = current_question.split('. ', 1)
        options = [part.strip() for part in question_parts[1].split('\n') if part.strip()]
        quiz_sessions[user_id]['options'] = options  # Save options in session

        blocks = [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"Question 1: {options[0]}"
                }
            },
            {
                "type": "actions",
                "block_id": "answer_block",
                "elements": [
                    {
                        "type": "checkboxes",
                        "action_id": "select_answer",
                        "options": [{"text": {"type": "plain_text", "text": opt}, "value": str(i+1)} for i, opt in enumerate(options[1:])]
                    },
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "Submit"
                        },
                        "value": "submit",
                        "action_id": "submit_answer"
                    }
                ]
            }
        ]

        app.logger.info(f"Sending blocks: {json.dumps(blocks, indent=2)}")
        return jsonify({
            "response_type": "in_channel",
            "blocks": blocks
        })
    except Exception as e:
        app.logger.error(f"Error processing start_quiz: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/slack/events', methods=['POST'])
def slack_events():
    app.logger.info("slack_events endpoint called")
    if 'X-Slack-Request-Timestamp' not in request.headers or 'X-Slack-Signature' not in request.headers:
        app.logger.error("Missing headers")
        return jsonify({"error": "Unauthorized"}), 403

    timestamp = request.headers['X-Slack-Request-Timestamp']
    signature = request.headers['X-Slack-Signature']
    
    if abs(time.time() - int(timestamp)) > 60 * 5:
        app.logger.error("Request timestamp too old")
        return jsonify({"error": "Unauthorized"}), 403

    if not verify_slack_request(request.get_data(), timestamp, signature):
        app.logger.error("Slack request verification failed")
        return jsonify({"error": "Unauthorized"}), 403

    try:
        payload = json.loads(request.form["payload"])
        app.logger.info(f"Payload received: {json.dumps(payload, indent=2)}")
        user_id = payload["user"]["id"]
        actions = payload["actions"][0]
        action_id = actions["action_id"]
        app.logger.info(f"Action ID: {action_id}")

        if user_id not in quiz_sessions:
            app.logger.error("Invalid session")
            return jsonify({"error": "Invalid session"}), 400

        session = quiz_sessions[user_id]
        options = session['options']  # Retrieve options from session

        if action_id == "select_answer":
            session["selected_answers"] = [option["value"] for option in actions.get("selected_options", [])]
            app.logger.info(f"Selected answers updated: {session['selected_answers']}")
            return jsonify({"status": "ok"})
        elif action_id == "submit_answer":
            app.logger.info("Submit button clicked")
            if not session["selected_answers"]:
                app.logger.error("No answers selected")
                return jsonify({"error": "No answers selected"}), 400

            current_question = session["questions"][session["current_question"]]
            correct_answer, explanation = lookup_table[current_question].split('. ', 1)

            correct_answers_set = set([answer.strip() for answer in correct_answer.split(',')])
            user_answers_set = set(session["selected_answers"])

            correct_answers_text = [options[int(i) - 1] for i in correct_answers_set]

            if user_answers_set == correct_answers_set:
                session["score"] += 1
                response_text = "That's correct!\n"
            else:
                response_text = f"That's incorrect. Correct answer(s): {', '.join(correct_answers_set)} ({', '.join(correct_answers_text)})\n"

            response_text += f"Explanation: {explanation}\n"
            app.logger.info(f"Response text: {response_text}")

            session["current_question"] += 1
            session["selected_answers"] = []

            app.logger.info(f"Current question index: {session['current_question']}")
            if session["current_question"] < session["num_questions"]:
                next_question = session["questions"][session["current_question"]]
                question_parts = next_question.split('. ', 1)
                options = [part.strip() for part in question_parts[1].split('\n') if part.strip()]
                session['options'] = options  # Save options for next question

                blocks = [
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": response_text
                        }
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"Question {session['current_question'] + 1}: {options[0]}"
                        }
                    },
                    {
                        "type": "actions",
                        "block_id": "answer_block",
                        "elements": [
                            {
                                "type": "checkboxes",
                                "action_id": "select_answer",
                                "options": [{"text": {"type": "plain_text", "text": opt}, "value": str(i+1)} for i, opt in enumerate(options[1:])]
                            },
                            {
                                "type": "button",
                                "text": {
                                    "type": "plain_text",
                                    "text": "Submit"
                                },
                                "value": "submit",
                                "action_id": "submit_answer"
                            }
                        ]
                    }
                ]

                app.logger.info(f"Sending blocks for next question: {json.dumps(blocks, indent=2)}")
                response = {
                    "response_type": "in_channel",
                    "replace_original": True,
                    "blocks": blocks
                }
                app.logger.info(f"Next question response: {json.dumps(response, indent=2)}")
                requests.post(payload["response_url"], json=response)
                return jsonify({"status": "ok"})
            else:
                response_text += f"Quiz completed! Your score is {session['score']}/{session['num_questions']}."
                del quiz_sessions[user_id]

                app.logger.info("Quiz completed")
                response = {
                    "response_type": "in_channel",
                    "replace_original": True,
                    "text": response_text
                }
                app.logger.info(f"Quiz completed response: {json.dumps(response, indent=2)}")
                requests.post(payload["response_url"], json=response)
                return jsonify({"status": "ok"})

        app.logger.error("Unknown action ID")
        return jsonify({"status": "ok"})
    except Exception as e:
        app.logger.error(f"Error processing slack_events: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/')
def index():
    return "Hello, Flask is running!"

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    app.run(host='0.0.0.0')