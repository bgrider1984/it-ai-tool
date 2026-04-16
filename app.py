import os
import uuid
from flask import Flask, render_template, request, jsonify
from openai import OpenAI

app = Flask(__name__)

api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise RuntimeError("Missing OPENAI_API_KEY")

client = OpenAI(api_key=api_key)

sessions = {}

# ----------------------------
# MULTI-ISSUE DETECTION
# ----------------------------
def detect_issues(text):
    t = text.lower()
    issues = []

    if "outlook" in t:
        issues.append("outlook")
    if "vpn" in t or "network" in t:
        issues.append("vpn")
    if "login" in t or "password" in t:
        issues.append("login")
    if "slow" in t or "lag" in t:
        issues.append("performance")

    return issues if issues else ["general"]

# ----------------------------
# AI NEXT STEP WITH CONFIDENCE
# ----------------------------
def ai_next_step(issues, history):
    prompt = f"""
You are a Tier 2 IT engineer.

Issues detected: {issues}

History:
{history}

Respond with:
1. Next best troubleshooting step
2. Confidence level (High / Medium / Low)
3. If applicable, provide a fix command label like: RUN_FIX: <short name>

Keep it concise.
"""

    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=250,
        temperature=0.3
    )

    return response.choices[0].message.content

# ----------------------------
# AUTO FIX SIMULATION
# ----------------------------
def run_fix_simulation(fix_name):
    fixes = {
        "restart_outlook": "Outlook process restarted successfully.",
        "reset_network": "Network adapter reset completed.",
        "flush_dns": "DNS cache cleared.",
        "new_profile": "New Outlook profile created."
    }

    return fixes.get(fix_name, "Fix executed.")

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
    session_id = data.get("session_id")

    if not session_id or session_id not in sessions:
        session_id = str(uuid.uuid4())
        sessions[session_id] = {
            "issues": [],
            "history": [],
            "last_fix": None
        }

    session = sessions[session_id]
    session["history"].append(user_input)

    user_text = user_input.lower()

    # ----------------------------
    # HANDLE FIX EXECUTION
    # ----------------------------
    if user_text.startswith("run fix"):
        if session["last_fix"]:
            result = run_fix_simulation(session["last_fix"])
            return jsonify({
                "session_id": session_id,
                "response": f"✅ Fix executed: {session['last_fix']}\n{result}"
            })
        else:
            return jsonify({
                "session_id": session_id,
                "response": "No fix available to run."
            })

    # ----------------------------
    # DETECT MULTIPLE ISSUES
    # ----------------------------
    detected = detect_issues(user_input)
    session["issues"] = list(set(session["issues"] + detected))

    # ----------------------------
    # AI DECISION ENGINE
    # ----------------------------
    ai_reply = ai_next_step(session["issues"], session["history"])

    # ----------------------------
    # EXTRACT FIX LABEL
    # ----------------------------
    if "RUN_FIX:" in ai_reply:
        fix_name = ai_reply.split("RUN_FIX:")[1].strip().split()[0]
        session["last_fix"] = fix_name

        ai_reply += f"\n\n👉 Type 'run fix' to execute: {fix_name}"

    return jsonify({
        "session_id": session_id,
        "response": ai_reply,
        "issues": session["issues"]
    })


if __name__ == "__main__":
    app.run(debug=True)
