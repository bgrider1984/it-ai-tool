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
        issues.append("network")
    if "login" in t:
        issues.append("login")

    return issues if issues else ["general"]

# ----------------------------
# AI FIX GENERATION
# ----------------------------
def ai_next_steps(issues, history, failed_fix=None):
    prompt = f"""
You are a Tier 2 IT engineer.

Issues: {issues}
History: {history}

"""

    if failed_fix:
        prompt += f"""
The previous fix FAILED: {failed_fix}

Now provide the NEXT best troubleshooting step.
Avoid repeating the same approach.
"""

    prompt += """
Return ONLY JSON:

{
  "message": "short explanation",
  "fixes": [
    {"name": "fix_id", "label": "Fix Name", "confidence": "High"}
  ]
}
"""

    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
        max_tokens=350
    )

    try:
        return json.loads(response.choices[0].message.content)
    except:
        return {
            "message": "Try restarting the application.",
            "fixes": []
        }

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
1. Control Panel → Mail
2. Show Profiles
3. Add new profile"""
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
    message = data.get("message", "")
    fix_request = data.get("run_fix")
    feedback = data.get("feedback")

    # ----------------------------
    # SESSION INIT
    # ----------------------------
    if not session_id or session_id not in sessions:
        session_id = str(uuid.uuid4())
        sessions[session_id] = {
            "history": [],
            "issues": [],
            "last_fix": None
        }

    session = sessions[session_id]

    # ----------------------------
    # RUN FIX → SHOW INSTRUCTIONS
    # ----------------------------
    if fix_request:
        session["last_fix"] = fix_request
        instructions = get_fix_instructions(fix_request)

        return jsonify({
            "session_id": session_id,
            "response": instructions,
            "fixes": [],
            "current_fix": fix_request,
            "ask_feedback": True
        })

    # ----------------------------
    # FEEDBACK LOOP (AUTO CONTINUE)
    # ----------------------------
    if feedback:
        fix = feedback.get("fix")
        result = feedback.get("result")

        # ❌ FAILED → AUTO CONTINUE TROUBLESHOOTING
        if result == "no":
            ai_data = ai_next_steps(
                session["issues"],
                session["history"],
                failed_fix=fix
            )

            return jsonify({
                "session_id": session_id,
                "response": "Got it — that didn’t resolve the issue. Trying next step...",
                "fixes": ai_data["fixes"]
            })

        # ✅ SUCCESS
        return jsonify({
            "session_id": session_id,
            "response": "Great — issue resolved 🎉",
            "fixes": []
        })

    # ----------------------------
    # NORMAL CHAT FLOW
    # ----------------------------
    session["history"].append(message)

    detected = detect_issues(message)
    session["issues"] = list(set(session["issues"] + detected))

    ai_data = ai_next_steps(session["issues"], session["history"])

    return jsonify({
        "session_id": session_id,
        "response": ai_data["message"],
        "fixes": ai_data["fixes"]
    })


if __name__ == "__main__":
    app.run(debug=True)
