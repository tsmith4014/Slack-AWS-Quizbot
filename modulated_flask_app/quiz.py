import random
from uuid import uuid4

quiz_sessions = {}

def start_new_session(user_id, num_questions, lookup_table):
    questions = list(lookup_table.keys())
    session_id = str(uuid4())
    quiz_sessions[user_id] = {
        "questions": random.sample(questions, num_questions),
        "current_question": 0,
        "score": 0,
        "num_questions": num_questions,
        "selected_answers": []
    }
    return quiz_sessions[user_id]

def get_current_question(user_id):
    session = quiz_sessions.get(user_id)
    if session:
        current_question = session["questions"][session["current_question"]]
        question_parts = current_question.split('. ', 1)
        options = [part.strip() for part in question_parts[1].split('\n') if part.strip()]
        return current_question, options
    return None, None

def update_session_with_answer(user_id, selected_answers):
    session = quiz_sessions.get(user_id)
    if session:
        session["selected_answers"] = selected_answers
        return session
    return None

def process_answer(user_id, lookup_table):
    session = quiz_sessions.get(user_id)
    if not session:
        return None, "Invalid session"

    current_question = session["questions"][session["current_question"]]
    correct_answer, explanation = lookup_table[current_question].split('. ', 1)

    correct_answers_set = set([answer.strip() for answer in correct_answer.split(',')])
    user_answers_set = set(session["selected_answers"])

    if user_answers_set == correct_answers_set:
        session["score"] += 1
        response_text = "That's correct!\n"
    else:
        response_text = f"That's incorrect. Correct answer(s): {', '.join(correct_answers_set)}\n"
    
    response_text += f"Explanation: {explanation}\n"

    session["current_question"] += 1
    session["selected_answers"] = []

    if session["current_question"] < session["num_questions"]:
        next_question, options = get_current_question(user_id)
        return response_text, next_question, options
    else:
        response_text += f"Quiz completed! Your score is {session['score']}/{session['num_questions']}."
        del quiz_sessions[user_id]
        return response_text, None, None