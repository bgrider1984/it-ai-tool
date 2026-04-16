import os
import json
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
# SIMPLE SESSION STORE (in-memory for now)
# ----------------------------
sessions = {}

# ----------------------------
# TROUBLESHOOTING FLOW (STATE MACHINE)
# ----------------------------
FLOW = {
    "start": {
        "question": "What type of device are you having issues with?",
        "options": ["Windows PC", "Mac", "Mobile Phone", "Printer"],
        "next": "device"
    },

    "device": {
        "question": "What type of issue are you experiencing?",
        "options": ["Network problem", "Software issue", "Hardware issue", "Other"],
        "next": "issue_type"
    },

    "issue_type": {
        "question": "Is the issue happening to just you or multiple users?",
        "options": ["Just me", "Multiple users"],
        "next": "scope"
    },

    "scope": {
        "question": "How long has this issue been happening?",
        "options": ["Just started", "A few days", "Weeks or longer"],
        "next": "duration"
    },

    "duration": {
        "question": "Final step: Do you see any error messages?",
        "options": ["Yes", "No"],
        "next": "final"
    },

    "final": {
        "question": "Thank you. I will analyze the issue and provide troubleshooting steps.",
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
# ASK (STATE ENGINE)
# ----------------------------
@app.route("/ask", methods=["POST"])
def ask():
    data = request.json
    session_id = data.get("session_id")

    if not session_id or session_id not in sessions:
        session_id = str(uuid.uuid4())
        sessions[session_id] = {"step": "start", "history": []}

    session = sessions[session_id]
    current_step = session["step"]

    user_input = data.get("message", "").strip()

    # ----------------------------
    # MOVE FORWARD IN FLOW
    # ----------------------------
    if user_input:
        session["history"].append(user_input)

        # simple step progression
        next_step = FLOW[current_step]["next"]

        # handle final step
        if next_step:
            session["step"] = next_step

        current_step = session["step"]

    node = FLOW[current_step]

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
