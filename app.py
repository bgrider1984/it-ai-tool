import os
import uuid
from flask import Flask, render_template, request, jsonify
from openai import OpenAI

app = Flask(__name__)

# ----------------------------
# OPENAI
# ----------------------------
api_key = os.getenv("OPENAI_API_KEY")

if not api_key:
    raise RuntimeError("Missing OPENAI_API_KEY")

client = OpenAI(api_key=api_key)

# ----------------------------
# SESSION STORE (simple in-memory)
# ----------------------------
sessions = {}

# ----------------------------
# WIZARD FLOW
# ----------------------------
FLOW = {
    "start": {
        "question": "What type of device are you having issues with?",
        "options": ["Windows PC", "Mac", "Mobile Phone", "Printer"],
        "next": "issue_type"
    },

    "issue_type": {
        "question": "What type of issue are you experiencing?",
        "options": ["Network problem", "Software issue", "Hardware issue", "Other"],
        "next": "scope"
    },

    "scope": {
        "question": "Is the issue happening to just you or multiple users?",
        "options": ["Just me", "Multiple users"],
        "next": "duration"
    },

    "duration": {
        "question": "How long has this issue been happening?",
        "options": ["Just started", "A few days", "Weeks or longer"],
        "next": "error"
    },

    "error": {
        "question": "Do you see any error messages?",
        "options": ["Yes", "No"],
        "next": "final"
    },

    "final": {
        "question": "Analyzing your issue...",
        "options": [],
        "next": None
    }
}

# ----------------------------
# HOME
# ----------------------------
@app.route("/")
def home():
    return render_template("index.html")

# ----------------------------
# ASK ENDPOINT
# ----------------------------
@app.route("/ask", methods=["POST"])
def ask():
    data = request.json

    session_id = data.get("session_id")
    user_input = data.get("message", "").strip()

    # ----------------------------
    # CREATE SESSION
    # ----------------------------
    if not session_id or session_id not in sessions:
        session_id = str(uuid.uuid4())
        sessions[session_id] = {
            "step": "start",
            "answers": {}
        }

    session = sessions[session_id]
    step = session["step"]

    node = FLOW[step]

    # ----------------------------
    # STORE ANSWER
    # ----------------------------
    if user_input:
        session["answers"][step] = user_input

        if node["next"]:
            session["step"] = node["next"]
            step = session["step"]
            node = FLOW[step]

    # ----------------------------
    # FINAL STEP → AI DIAGNOSIS
    # ----------------------------
    if step == "final":
        summary = session["answers"]

        prompt = f"""
You are a senior enterprise IT support engineer.

A user has reported an issue. Here are the details:

Device: {summary.get("start", "Unknown")}
Issue Type: {summary.get("issue_type", "Unknown")}
Scope: {summary.get("scope", "Unknown")}
Duration: {summary.get("duration", "Unknown")}
Error Messages: {summary.get("error", "Unknown")}

Provide:

1. Most likely causes (ranked)
2. Step-by-step troubleshooting
3. Any useful Windows/Mac commands
4. When to escalate to IT support

Be concise and technical.
"""

        response = client.chat.completions.create(
            model="gpt-4.1-mini",
            max_tokens=600,
            messages=[
                {"role": "system", "content": "You are a Tier 2/3 IT support engineer."},
                {"role": "user", "content": prompt}
            ]
        )

        return jsonify({
            "session_id": session_id,
            "response": response.choices[0].message.content,
            "options": []
        })

    # ----------------------------
    # NORMAL STEP RESPONSE
    # ----------------------------
    return jsonify({
        "session_id": session_id,
        "response": node["question"],
        "options": node["options"]
    })


# ----------------------------
# RUN
# ----------------------------
if __name__ == "__main__":
    app.run(debug=True)
