import os
import uuid
from flask import Flask, render_template, request, jsonify
from openai import OpenAI

app = Flask(__name__)

api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=api_key)

sessions = {}

FLOW = {
    "device": {
        "question": "What type of device are you using?",
        "options": ["Windows PC", "Mac", "Mobile Phone", "Printer"],
        "next": "issue_type"
    },
    "issue_type": {
        "question": "What type of issue are you experiencing?",
        "options": ["Network problem", "Software issue", "Hardware issue", "Other"],
        "next": "scope"
    },
    "scope": {
        "question": "Is this happening to just you or multiple users?",
        "options": ["Just me", "Multiple users"],
        "next": "duration"
    },
    "duration": {
        "question": "How long has this been happening?",
        "options": ["Just started", "A few days", "Weeks or longer"],
        "next": "error"
    },
    "error": {
        "question": "Do you see any error messages?",
        "options": ["Yes", "No"],
        "next": "final"
    },
    "final": {
        "question": "",
        "options": [],
        "next": None
    }
}


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/ask", methods=["POST"])
def ask():
    data = request.json
    user_input = data.get("message", "").strip()
    session_id = data.get("session_id")

    # ----------------------------
    # INIT SESSION
    # ----------------------------
    if not session_id or session_id not in sessions:
        session_id = str(uuid.uuid4())
        sessions[session_id] = {
            "step": "detect",
            "issue": None,
            "answers": {}
        }

    session = sessions[session_id]

    # ----------------------------
    # STEP 1: DETECT ISSUE
    # ----------------------------
    if session["step"] == "detect":
        if user_input:
            response = client.chat.completions.create(
                model="gpt-4.1-mini",
                max_tokens=100,
                messages=[
                    {
                        "role": "system",
                        "content": "Classify the IT issue in a short label."
                    },
                    {"role": "user", "content": user_input}
                ]
            )

            issue = response.choices[0].message.content.strip()

            session["issue"] = issue
            session["step"] = "confirm_issue"

            return jsonify({
                "session_id": session_id,
                "response": f"I detected: {issue}. Is this correct?",
                "options": ["Yes", "No"]
            })

        return jsonify({
            "session_id": session_id,
            "response": "Describe your issue (e.g. Outlook not opening).",
            "options": []
        })

    # ----------------------------
    # STEP 2: CONFIRM ISSUE (FIXED)
    # ----------------------------
    if session["step"] == "confirm_issue":
        if user_input.lower() == "no":
            session["step"] = "detect"
            session["issue"] = None

            return jsonify({
                "session_id": session_id,
                "response": "Please re-describe your issue.",
                "options": []
            })

        if user_input.lower() == "yes":
            session["step"] = "device"

    # ----------------------------
    # NORMAL FLOW
    # ----------------------------
    step = session["step"]
    node = FLOW[step]

    if user_input and step in FLOW:
        session["answers"][step] = user_input

        if node["next"]:
            session["step"] = node["next"]
            step = session["step"]
            node = FLOW[step]

    # ----------------------------
    # FINAL STEP
    # ----------------------------
    if step == "final":
        summary = session["answers"]

        prompt = f"""
Issue: {session['issue']}
Device: {summary.get("device")}
Type: {summary.get("issue_type")}
Scope: {summary.get("scope")}
Duration: {summary.get("duration")}
Error: {summary.get("error")}

Provide:
- Likely causes
- Step-by-step fix
- Commands
- Escalation guidance
"""

        response = client.chat.completions.create(
            model="gpt-4.1-mini",
            max_tokens=600,
            messages=[
                {"role": "system", "content": "You are a senior IT support engineer."},
                {"role": "user", "content": prompt}
            ]
        )

        return jsonify({
            "session_id": session_id,
            "response": response.choices[0].message.content,
            "options": []
        })

    return jsonify({
        "session_id": session_id,
        "response": node["question"],
        "options": node["options"]
    })


if __name__ == "__main__":
    app.run(debug=True)
