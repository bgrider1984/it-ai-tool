import os
import uuid
import json
from flask import Flask, render_template, request, jsonify
from openai import OpenAI

app = Flask(__name__)

api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise RuntimeError("Missing OPENAI_API_KEY")

client = OpenAI(api_key=api_key)

sessions = {}

# ----------------------------
# ISSUE DETECTION
# ----------------------------
def detect_issues(text):
    t = text.lower()
    issues = []

    if "outlook" in t:
        issues.append("outlook")
    if "vpn" in t or "network" in t:
        issues.append("vpn")
    if "login" in t:
        issues.append("login")

    return issues if issues else ["general"]

# ----------------------------
# AI FIX SUGGESTIONS
# ----------------------------
def ai_next_steps(issues, history):
    prompt = f"""
You are a Tier 2 IT engineer.

Issues: {issues}
History: {history}

Return ONLY JSON:

{{
  "message": "short explanation",
  "fixes": [
    {{"name": "restart_outlook", "label": "Restart Outlook", "confidence": "High"}},
    {{"name": "safe_mode", "label": "Open in Safe Mode", "confidence": "Medium"}},
    {{"name": "new_profile", "label": "Create New Profile", "confidence": "Low"}}
  ]
}}
"""

    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
        max_tokens=300
    )

    try:
        return json.loads(response.choices[0].message.content)
    except:
        return {"message": "Try restarting Outlook.", "fixes": []}

# ----------------------------
# FIX INSTRUCTIONS
# ----------------------------
def get_fix_instructions(fix):
    steps = {
        "restart_outlook": """Restart Outlook:
1. Open Task Manager (Ctrl+Shift+Esc)
2. End Microsoft Outlook
3. Reopen Outlook""",

        "safe_mode": """Safe Mode:
1. Win + R
2. outlook.exe /safe
3. Press Enter""",

        "new_profile": """New Profile:
1. Control Panel
2. Mail
3. Show Profiles
4. Add new profile""",

        "reset_network": """Reset Network:
1. Win + R
2. ncpa.cpl
3. Disable/Enable adapter"""
    }

    return steps.get(fix, "No instructions available.")

# ----------------------------
# ROUTES
# ----------------------------
@app.route("/")
def home():
    return render_template("index.html")

@app.route("/ask", methods=["POST"])
def ask():
    data = request.json
    session_id = data.get("session_id")
    user_input = data.get("message", "")
    fix_request = data.get("run_fix")
    feedback = data.get("feedback")

    # ----------------------------
    # CREATE SESSION
    # ----------------------------
    if not session_id or session_id not in sessions:
        session_id = str(uuid.uuid4())
        sessions[session_id] = {
            "history": [],
            "issues": [],
            "last_fix": None,
            "fix_results": {}
        }

    session = sessions[session_id]

    # ----------------------------
    # FEEDBACK LOOP (NEW)
    # ----------------------------
    if feedback:
        fix = feedback.get("fix")
        result = feedback.get("result")

        session["fix_results"][fix] = result

        # If failed → continue AI troubleshooting
        if result == "no":
            ai_data = ai_next_steps(session["issues"], session["history"])
            return jsonify({
                "session_id": session_id,
                "response": "Got it — continuing troubleshooting...",
                "fixes": ai_data["fixes"]
            })

        return jsonify({
            "session_id": session_id,
            "response": "Great — issue marked as resolved 🎉",
            "fixes": []
        })

    # ----------------------------
    # RUN FIX → SHOW INSTRUCTIONS
    # ----------------------------
    if fix_request:
        instructions = get_fix_instructions(fix_request)
        session["last_fix"] = fix_request

        return jsonify({
            "session_id": session_id,
            "response": instructions,
            "fixes": [],
            "ask_feedback": True,
            "current_fix": fix_request
        })

    # ----------------------------
    # NORMAL CHAT
    # ----------------------------
    session["history"].append(user_input)

    detected = detect_issues(user_input)
    session["issues"] = list(set(session["issues"] + detected))

    ai_data = ai_next_steps(session["issues"], session["history"])

    return jsonify({
        "session_id": session_id,
        "response": ai_data["message"],
        "fixes": ai_data["fixes"]
    })


if __name__ == "__main__":
    app.run(debug=True)
