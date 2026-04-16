import os
import uuid
import json
from flask import Flask, render_template, request, jsonify
from openai import OpenAI

app = Flask(__name__)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

sessions = {}

# ----------------------------
# SESSION INIT
# ----------------------------
def get_session(session_id):
    if not session_id or session_id not in sessions:
        session_id = str(uuid.uuid4())
        sessions[session_id] = {
            "history": [],
            "issue": None,
            "failed_steps": []
        }
    return session_id, sessions[session_id]

# ----------------------------
# INTENT SWITCH DETECTION
# ----------------------------
def is_new_issue(prev_issue, message):
    triggers = ["new issue", "actually", "different", "instead", "switch", "forget"]
    if prev_issue is None:
        return True
    return any(t in message.lower() for t in triggers)

# ----------------------------
# TIER 2 AI ENGINE
# ----------------------------
def ai_copilot(issue, history, failed_steps):

    prompt = f"""
You are a Tier 2 IT support engineer.

Your job:
- Diagnose the issue
- Avoid repeating failed steps
- Escalate intelligently if needed

User issue context:
{issue}

Conversation history:
{history}

Failed steps (DO NOT REPEAT THESE):
{failed_steps}

Return ONLY valid JSON:

{{
  "issue_summary": "short interpretation of the problem",
  "likely_cause": "what is probably happening",
  "confidence": "low|medium|high",
  "steps": [
    {{
      "id": "step_name",
      "action": "what to do",
      "why": "why this step is being done"
    }}
  ],
  "escalation": "when to escalate"
}}
"""

    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
        max_tokens=600
    )

    try:
        return json.loads(response.choices[0].message.content)
    except:
        return {
            "issue_summary": "Unable to parse issue",
            "likely_cause": "Unknown",
            "confidence": "low",
            "steps": [
                {
                    "id": "basic_restart",
                    "action": "Restart the system",
                    "why": "Reset state to clear transient issues"
                }
            ],
            "escalation": "If issue persists, escalate to Tier 3"
        }

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

    # ----------------------------
    # INTENT RESET
    # ----------------------------
    if is_new_issue(session["issue"], message):
        session["history"] = []
        session["failed_steps"] = []

    session["history"].append(message)

    # ----------------------------
    # AI CALL
    # ----------------------------
    result = ai_copilot(
        issue=message,
        history=session["history"],
        failed_steps=session["failed_steps"]
    )

    session["issue"] = result["issue_summary"]

    return jsonify({
        "session_id": session_id,
        "response": result,
    })


if __name__ == "__main__":
    app.run(debug=True)
