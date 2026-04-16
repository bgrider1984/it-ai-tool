import os
import uuid
from flask import Flask, render_template, request, jsonify
from openai import OpenAI

app = Flask(__name__)

# ----------------------------
# OPENAI SETUP
# ----------------------------
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise RuntimeError("Missing OPENAI_API_KEY")

client = OpenAI(api_key=api_key)

# ----------------------------
# SESSION STORE
# ----------------------------
sessions = {}

# ----------------------------
# WIZARD FLOW
# ----------------------------
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
        "question": "How long has this issue been happening?",
        "options": ["Just started", "A few days", "Weeks or longer"],
        "next": "error"
    },
    "error": {
        "question": "Do you see any error messages?",
        "options": ["Yes", "No"],
        "next": "final"
    }
}

# ----------------------------
# HOME
# ----------------------------
@app.route("/")
def home():
    return render_template("index.html")

# ----------------------------
# MAIN ENDPOINT
# ----------------------------
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
    step = session["step"]

    # ----------------------------
    # STEP 1: DETECT ISSUE
    # ----------------------------
    if step == "detect":
        if user_input:
            response = client.chat.completions.create(
                model="gpt-4.1-mini",
                max_tokens=80,
                messages=[
                    {
                        "role": "system",
                        "content": "Classify IT issue in max 6 words."
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
    # STEP 2: CONFIRM ISSUE (FIXED FLOW CONTINUATION)
    # ----------------------------
    if step == "confirm_issue":
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

            # 🔥 IMPORTANT FIX: immediately continue flow
            node = FLOW["device"]

            return jsonify({
                "session_id": session_id,
                "response": node["question"],
                "options": node["options"]
            })

        return jsonify({
            "session_id": session_id,
            "response": "Please confirm: Is this correct?",
            "options": ["Yes", "No"]
        })

    # ----------------------------
    # NORMAL WIZARD FLOW
    # ----------------------------
    if step in FLOW:
        node = FLOW[step]

        if user_input:
            session["answers"][step] = user_input

            if node["next"]:
                session["step"] = node["next"]
                step = session["step"]
                node = FLOW[step]

        return jsonify({
            "session_id": session_id,
            "response": node["question"],
            "options": node["options"]
        })

    # ----------------------------
    # FINAL STEP (AI DIAGNOSIS)
    # ----------------------------
    if step == "final":
        summary = session["answers"]

        prompt = f"""
Issue: {session.get('issue')}

Device: {summary.get("device")}
Issue Type: {summary.get("issue_type")}
Scope: {summary.get("scope")}
Duration: {summary.get("duration")}
Error Messages: {summary.get("error")}

Provide:
1. Likely causes (ranked)
2. Step-by-step troubleshooting
3. Commands if applicable
4. Escalation guidance
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

    # ----------------------------
    # SAFETY FALLBACK
    # ----------------------------
    return jsonify({
        "session_id": session_id,
        "response": "Let's continue troubleshooting.",
        "options": []
    })


# ----------------------------
# RUN APP
# ----------------------------
if __name__ == "__main__":
    app.run(debug=True)
