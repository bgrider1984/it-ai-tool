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
# AI MULTI-FIX GENERATOR
# ----------------------------
def ai_next_steps(issues, history):
    prompt = f"""
You are a Tier 2 IT engineer.

Issues: {issues}
History: {history}

Respond ONLY in JSON like this:

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
        return {
            "message": "Try restarting the application.",
            "fixes": []
        }

# ----------------------------
# FIX SIMULATION
# ----------------------------
def run_fix(fix):
    results = {
        "restart_outlook": "Outlook restarted successfully.",
        "safe_mode": "Opened Outlook in Safe Mode.",
        "new_profile": "New profile created.",
        "reset_network": "Network reset complete."
    }
    return results.get(fix, "Fix executed.")

# ----------------------------
# ROUTES
# ----------------------------
@app.route("/")
def home():
    return render_template("index.html")

@app.route("/ask", methods=["POST"])
def ask():
    data = request.json
    user_input = data.get("message", "")
    fix_request = data.get("run_fix")
    session_id = data.get("session_id")

    if not session_id or session_id not in sessions:
        session_id = str(uuid.uuid4())
        sessions[session_id] = {
            "history": [],
            "issues": []
        }

    session = sessions[session_id]

    # ----------------------------
    # RUN FIX
    # ----------------------------
    if fix_request:
        result = run_fix(fix_request)
        return jsonify({
            "session_id": session_id,
            "response": f"✅ {result}",
            "fixes": []
        })

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
