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
# SESSION STORAGE
# ----------------------------
sessions = {}

# ----------------------------
# ISSUE DETECTION
# ----------------------------
def detect_issue(text):
    t = text.lower()

    rules = {
        "outlook": ["outlook", "email", "mail", "exchange"],
        "vpn": ["vpn", "remote", "network", "dns", "internet"],
        "login": ["login", "sign in", "password", "credentials", "locked out"],
        "printer": ["printer", "print", "spooler"],
        "software": ["crash", "freeze", "not responding", "app closes"],
        "performance": ["slow", "lag", "freezing"]
    }

    for k, v in rules.items():
        if any(x in t for x in v):
            return k

    return "general"

# ----------------------------
# PLAYBOOKS (GUIDED FIXES)
# ----------------------------
PLAYBOOKS = {
    "outlook": {
        "label": "Outlook Safe Mode Check",
        "steps": [
            "Press Windows + R",
            "Type: outlook.exe /safe",
            "Press Enter",
            "Check if Outlook opens"
        ]
    },
    "vpn": {
        "label": "Reset Network Adapter",
        "steps": [
            "Press Windows + R",
            "Type: ncpa.cpl and press Enter",
            "Right-click your network adapter",
            "Click Disable, wait 5 seconds, then Enable",
            "Test VPN again"
        ]
    },
    "login": {
        "label": "Check Login Status",
        "steps": [
            "Confirm Caps Lock is OFF",
            "Try password again carefully",
            "If still failing, reset password via IT portal"
        ]
    }
}

# ----------------------------
# SYSTEM PROMPT (TIER 2 ENGINE MODE)
# ----------------------------
SYSTEM_PROMPT = """
You are a Tier 2 IT support engineer.

Rules:
- Be extremely concise
- Diagnose quickly
- Give max 3 steps
- No explanations unless necessary
- Ask only 1 follow-up question if required
"""

# ----------------------------
# HOME
# ----------------------------
@app.route("/")
def home():
    return render_template("index.html")

# ----------------------------
# CHAT ENDPOINT
# ----------------------------
@app.route("/ask", methods=["POST"])
def ask():
    data = request.json
    user_input = data.get("message", "")
    session_id = data.get("session_id")

    if not session_id or session_id not in sessions:
        session_id = str(uuid.uuid4())
        sessions[session_id] = {"messages": []}

    session = sessions[session_id]

    # detect issue type
    issue_type = detect_issue(user_input)

    session["messages"].append({"role": "user", "content": user_input})

    messages = [
        {
            "role": "system",
            "content": SYSTEM_PROMPT + f"\nDetected Issue: {issue_type}"
        }
    ]

    messages.extend(session["messages"][-6:])

    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=messages,
        max_tokens=450,
        temperature=0.3
    )

    reply = response.choices[0].message.content

    session["messages"].append({"role": "assistant", "content": reply})

    # build actions based on detected issue
    actions = []
    if issue_type in PLAYBOOKS:
        actions.append({
            "id": issue_type,
            "label": PLAYBOOKS[issue_type]["label"]
        })

    return jsonify({
        "session_id": session_id,
        "response": reply,
        "actions": actions
    })

# ----------------------------
# ACTION ENDPOINT (GUIDED STEPS)
# ----------------------------
@app.route("/action", methods=["POST"])
def action():
    data = request.json
    action_id = data.get("action_id")
    step = data.get("step", 0)

    if action_id not in PLAYBOOKS:
        return jsonify({"error": "invalid action"}), 400

    steps = PLAYBOOKS[action_id]["steps"]

    if step >= len(steps):
        return jsonify({
            "done": True,
            "message": "Check complete. Tell me what happened."
        })

    return jsonify({
        "step": step,
        "instruction": steps[step],
        "next_step": step + 1
    })

# ----------------------------
# RUN
# ----------------------------
if __name__ == "__main__":
    app.run(debug=True)
