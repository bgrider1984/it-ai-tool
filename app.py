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
    if "login" in t or "password" in t:
        issues.append("auth")

    return issues if issues else ["general"]

# ----------------------------
# ROOT CAUSE ENGINE
# ----------------------------
def analyze_root_cause(failed_fixes, issues):
    pattern_score = {
        "dns": 0,
        "profile": 0,
        "network": 0,
        "auth": 0,
        "outlook": 0
    }

    for fix in failed_fixes:
        if fix in ["reset_network", "flush_dns"]:
            pattern_score["dns"] += 2
            pattern_score["network"] += 1

        if fix in ["new_profile"]:
            pattern_score["profile"] += 3

        if fix in ["restart_outlook", "safe_mode"]:
            pattern_score["outlook"] += 2

    best = max(pattern_score, key=pattern_score.get)

    if pattern_score[best] == 0:
        return None

    return {
        "root_cause": best,
        "confidence": "Medium" if pattern_score[best] < 3 else "High",
        "reasoning": f"Pattern detected from failed fixes: {failed_fixes}"
    }

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
Previous fix FAILED: {failed_fix}
Avoid repeating same approach. Change strategy.
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
            "message": "Try restarting Outlook.",
            "fixes": []
        }

# ----------------------------
# FIX INSTRUCTIONS
# ----------------------------
def get_fix_instructions(fix):
    steps = {
        "restart_outlook": """Restart Outlook:
1. Open Task Manager
2. End Outlook
3. Reopen""",

        "safe_mode": """Safe Mode:
1. Win + R
2. outlook.exe /safe""",

        "new_profile": """New Profile:
1. Control Panel → Mail
2. Show Profiles → Add""",

        "reset_network": """Network Reset:
1. ncpa.cpl
2. Disable/Enable adapter"""
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
            "failed_fixes": [],
            "last_fix": None
        }

    session = sessions[session_id]

    # ----------------------------
    # RUN FIX
    # ----------------------------
    if fix_request:
        session["last_fix"] = fix_request
        instructions = get_fix_instructions(fix_request)

        return jsonify({
            "session_id": session_id,
            "response": instructions,
            "fixes": [],
            "ask_feedback": True,
            "current_fix": fix_request
        })

    # ----------------------------
    # FEEDBACK LOOP + RCA
    # ----------------------------
    if feedback:
        fix = feedback.get("fix")
        result = feedback.get("result")

        if result == "no":
            session["failed_fixes"].append(fix)

            rca = analyze_root_cause(session["failed_fixes"], session["issues"])
            ai_data = ai_next_steps(session["issues"], session["history"], failed_fix=fix)

            response_text = "Got it — continuing troubleshooting..."

            if rca:
                response_text += f"\n\n🔍 Root Cause Analysis:\nLikely: {rca['root_cause']}\nConfidence: {rca['confidence']}\nReason: {rca['reasoning']}"

            return jsonify({
                "session_id": session_id,
                "response": response_text,
                "fixes": ai_data["fixes"]
            })

        return jsonify({
            "session_id": session_id,
            "response": "Great — issue resolved 🎉",
            "fixes": []
        })

    # ----------------------------
    # NORMAL CHAT
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
