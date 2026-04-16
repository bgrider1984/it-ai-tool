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
            "issue": None,
            "step_index": 0
        }
    return session_id, sessions[session_id]

# ----------------------------
# INTENT SWITCH
# ----------------------------
def is_new_issue(prev, msg):
    triggers = ["new issue", "actually", "different", "instead", "switch", "forget"]
    if prev is None:
        return True
    return any(t in msg.lower() for t in triggers)

# ----------------------------
# TIER 2 ACTIONABLE ENGINE
# ----------------------------
def ai_engine(issue, history):

    prompt = f"""
You are a Tier 2 IT engineer.

Convert troubleshooting into ACTIONABLE steps.

RULES:
- Every step MUST include instructions (click-by-click or command-by-command)
- Never give vague steps
- Always include expected result
- Always include next escalation path if step fails
- Choose a START HERE step

Return ONLY JSON:

{{
  "issue_summary": "...",
  "likely_cause": "...",
  "confidence": "low|medium|high",
  "start_here": 0,
  "steps": [
    {{
      "title": "Step name",
      "instructions": ["step 1", "step 2", "step 3"],
      "expected": "what should happen",
      "if_failed": "next diagnostic direction"
    }}
  ]
}}

Issue:
{issue}

History:
{history}
"""

    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
        max_tokens=800
    )

    try:
        return response.choices[0].message.content
    except:
        return None

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
    # DETECT ISSUE
    # ----------------------------
    issue = message  # keep raw context for AI

    if is_new_issue(session["issue"], message):
        session["step_index"] = 0
        session["history"] = []

    session["history"].append(message)
    session["issue"] = issue

    # ----------------------------
    # AI CALL
    # ----------------------------
    raw = ai_engine(issue, session["history"])

    return jsonify({
        "session_id": session_id,
        "response": raw
    })


if __name__ == "__main__":
    app.run(debug=True)
