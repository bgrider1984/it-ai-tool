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
            "last_issue": None
        }
    return session_id, sessions[session_id]

# ----------------------------
# INTENT SWITCH
# ----------------------------
def is_new_issue(prev, msg):
    triggers = ["new issue", "actually", "instead", "different", "switch", "forget"]
    if prev is None:
        return True
    return any(t in msg.lower() for t in triggers)

# ----------------------------
# HELP DESK COPILOT ENGINE (FAST MODE)
# ----------------------------
def helpdesk_response(issue, history):

    prompt = f"""
You are a FAST Tier 2 IT Help Desk Copilot.

RULES:
- Be extremely concise
- No long explanations
- Prioritize fastest likely fix FIRST
- Max 3–5 steps total
- Format like a real IT help desk technician
- Always include a "Try this first" section
- Only escalate if needed

FORMAT:

🔴 TRY THIS FIRST:
- step 1
- step 2

🟡 IF THAT DOESN'T WORK:
- step 1
- step 2

🔵 IF STILL NOT FIXED:
- escalation path

Issue:
{issue}

History:
{history}
"""

    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
        max_tokens=450
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

    # reset context on new issue
    if is_new_issue(session["last_issue"], message):
        session["history"] = []

    session["history"].append(message)
    session["last_issue"] = message

    reply = helpdesk_response(message, session["history"])

    return jsonify({
        "session_id": session_id,
        "response": reply
    })


if __name__ == "__main__":
    app.run(debug=True)
