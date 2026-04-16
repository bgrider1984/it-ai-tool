import os
import uuid
from flask import Flask, render_template, request, jsonify
from openai import OpenAI

app = Flask(__name__)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

sessions = {}

# ----------------------------
# SESSION
# ----------------------------
def get_session(session_id):
    if not session_id or session_id not in sessions:
        session_id = str(uuid.uuid4())
        sessions[session_id] = {
            "history": [],
            "last_issue": None,
            "last_response": ""
        }
    return session_id, sessions[session_id]

# ----------------------------
# INTENT SWITCH DETECTION
# ----------------------------
def is_new_issue(prev, msg):
    triggers = ["new issue", "actually", "instead", "different", "switch", "forget"]
    if prev is None:
        return True
    return any(t in msg.lower() for t in triggers)

# ----------------------------
# JUNIOR TECH COPILOT ENGINE
# ----------------------------
def generate_help(issue, history):

    prompt = f"""
You are a senior IT technician helping a junior technician.

Rules:
- Keep answers simple, direct, and practical
- No enterprise language
- No workflows or systems
- Provide step-by-step troubleshooting
- If needed, adapt steps based on failure feedback
- Always prioritize the most likely fix first

Return format:

Problem Summary:
Cause:
Steps:
1.
2.
3.
What to do if it doesn't work:

Issue:
{issue}

History:
{history}
"""

    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
        max_tokens=600
    )

    return response.choices[0].message.content

# ----------------------------
# ROUTE
# ----------------------------
@app.route("/")
def home():
    return render_template("index.html")

@app.route("/ask", methods=["POST"])
def ask():

    data = request.json

    session_id = data.get("session_id")
    message = data.get("message", "")

    session_id, session = get_session(session_id)

    # reset if new issue
    if is_new_issue(session["last_issue"], message):
        session["history"] = []

    session["history"].append(message)
    session["last_issue"] = message

    # generate response
    reply = generate_help(message, session["history"])

    return jsonify({
        "session_id": session_id,
        "response": reply
    })


if __name__ == "__main__":
    app.run(debug=True)
