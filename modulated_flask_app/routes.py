from flask import request, jsonify
import json
import logging
import requests
from utils import verify_slack_request, load_lookup_table
from quiz import start_new_session, get_current_question, update_session_with_answer, process_answer

lookup_table = load_lookup_table('lookup_table.json')

def init_routes(app):
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

        if not verify_slack_request(request.get_data(), timestamp, signature, app.config['SLACK_SIGNING_SECRET']):
            app.logger.error("Slack request verification failed")
            return jsonify({"error": "Unauthorized"}), 403

        try:
            data = request.form
            app.logger.info(f"Form data: {data}")
            num_questions = int(data.get('text', 5))
            user_id = data.get('user_id')
            session = start_new_session(user_id, num_questions, lookup_table)

            current_question, options = get_current_question(user_id)
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

        if not verify_slack_request(request.get_data(), timestamp, signature, app.config['SLACK_SIGNING_SECRET']):
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

            if action_id == "select_answer":
                session["selected_answers"] = [option["value"] for option in actions.get("selected_options", [])]
                app.logger.info(f"Selected answers updated: {session['selected_answers']}")
                return jsonify({"status": "ok"})
            elif action_id == "submit_answer":
                app.logger.info("Submit button clicked")
                if not session["selected_answers"]:
                    app.logger.error("No answers selected")
                    return jsonify({"error": "No answers selected"}), 400

                response_text, next_question, options = process_answer(user_id, lookup_table)
                app.logger.info(f"Response text: {response_text}")

                if next_question:
                    blocks = [
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