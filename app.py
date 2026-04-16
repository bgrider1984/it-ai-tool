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

MEMORY_FILE = "memory.json"

# ----------------------------
# LOAD MEMORY
# ----------------------------
def load_memory():
    if not os.path.exists(MEMORY_FILE):
        return {}
    with open(MEMORY_FILE, "r") as f:
        return json.load(f)

def save_memory(data):
    with open(MEMORY_FILE, "w") as f:
        json.dump(data, f, indent=2)

memory = load_memory()

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
        issues.append("auth")

    return issues if issues else ["general"]

# ----------------------------
# UPDATE MEMORY (NEW)
# ----------------------------
def update_memory(issue, fix, result):
    if issue not in memory:
        memory[issue] = {}

    if fix not in memory[issue]:
        memory[issue][fix] = {"success": 0, "fail": 0}

    if result == "yes":
        memory[issue][fix]["success"] += 1
    else:
        memory[issue][fix]["fail"] += 1

    save_memory(memory)

# ----------------------------
# GET MEMORY INSIGHTS (NEW)
# ----------------------------
def get_memory_insights(issue):
    if issue not in memory:
        return ""

    stats = memory[issue]

    ranked = sorted(
        stats.items(),
        key=lambda x: x[1]["success"] - x[1]["fail"],
        reverse=True
    )

    if not ranked:
        return ""

    best = ranked[0]

    return f"Previous successful fix pattern: {best[0]} (Success: {best[1]['success']})"

# ----------------------------
# ROOT CAUSE ENGINE
# ----------------------------
def analyze_root_cause(failed_fixes, issues):
    if not failed_fixes:
        return None

    score = {"network":0,"profile":0,"auth":0,"outlook":0}

    for f in failed_fixes:
        if f in ["reset_network"]:
            score["network"] += 2
        if f in ["new_profile"]:
            score["profile"] += 2
        if f in ["safe_mode"]:
            score["outlook"] += 2

    best = max(score, key=score.get)

    if score[best] == 0:
        return None

    return {
        "root_cause": best,
        "confidence": "High" if score[best] >= 3 else "Medium"
    }

# ----------------------------
# AI ENGINE
# ----------------------------
def ai_next_steps(issues, history, memory_hint="", failed_fix=None):
    prompt = f"""
You are a Tier 2 IT engineer.

Issues: {issues}
History: {history}

Memory Insight:
{memory_hint}

"""

    if failed_fix:
        prompt += f"\nPrevious fix failed: {failed_fix}\nAvoid repeating similar steps."

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
        return {"message": "Try restarting Outlook.", "fixes": []}

# ----------------------------
# FIX INSTRUCTIONS
# ----------------------------
def get_fix_instructions(fix):
    steps = {
        "restart_outlook": "1. Task Manager → End Outlook → Reopen",
        "safe_mode": "Win + R → outlook.exe /safe",
        "new_profile": "Control Panel → Mail → Profiles → Add",
        "reset_network": "ncpa.cpl → disable/enable adapter"
    }
    return steps.get(fix, "No instructions available.")

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
    fix_request = data.get("run_fix")
    feedback = data.get("feedback")

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
    # FEEDBACK + MEMORY UPDATE
    # ----------------------------
    if feedback:
        fix = feedback.get("fix")
        result = feedback.get("result")

        primary_issue = session["issues"][0] if session["issues"] else "general"

        update_memory(primary_issue, fix, result)

        if result == "no":
            session["failed_fixes"].append(fix)

            rca = analyze_root_cause(session["failed_fixes"], session["issues"])

            memory_hint = get_memory_insights(primary_issue)

            ai_data = ai_next_steps(
                session["issues"],
                session["history"],
                memory_hint=memory_hint,
                failed_fix=fix
            )

            response_text = "Continuing troubleshooting..."

            if rca:
                response_text += f"\n\n🔍 Root Cause: {rca['root_cause']} ({rca['confidence']})"

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
    # NORMAL FLOW
    # ----------------------------
    session["history"].append(message)

    detected = detect_issues(message)
    session["issues"] = list(set(session["issues"] + detected))

    memory_hint = get_memory_insights(session["issues"][0])

    ai_data = ai_next_steps(
        session["issues"],
        session["history"],
        memory_hint=memory_hint
    )

    return jsonify({
        "session_id": session_id,
        "response": ai_data["message"],
        "fixes": ai_data["fixes"]
    })


if __name__ == "__main__":
    app.run(debug=True)
