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
# SIMPLE IN-MEMORY SESSION STORE
# ----------------------------
sessions = {}

# ----------------------------
# ISSUE DETECTION
# ----------------------------
def detect_issue(text):
    t = text.lower()

    rules = {
        "outlook": ["outlook", "email", "mail", "exchange"],
        "vpn": ["vpn", "dns", "network", "internet", "wifi"],
        "login": ["login", "sign in", "password", "locked out"],
        "printer": ["printer", "print"],
        "software": ["crash", "freeze", "not responding"],
        "performance": ["slow", "lag"]
    }

    for issue, keywords in rules.items():
        if any(k in t for k in keywords):
            return issue

    return "general"

# ----------------------------
# PLAYBOOKS (GUIDED TROUBLESHOOTING)
# ----------------------------
PLAYBOOKS = {
    "outlook": [
        "Step 1: Press Windows + R",
        "Step 2: Type outlook.exe /safe",
        "Step 3: Press Enter",
        "Step 4: Tell me if Outlook opens in Safe Mode"
    ],
    "vpn": [
        "Step 1: Press Windows + R",
        "Step 2: Type ncpa.cpl",
        "Step 3: Disable then re-enable your network adapter",
        "Step 4: Test VPN again"
    ],
    "login": [
        "Step 1: Confirm Caps Lock is OFF",
        "Step 2: Re-enter credentials carefully",
        "Step 3: Try password reset if needed"
    ]
}

# ----------------------------
# SYSTEM PROMPT (TIER 2 STYLE)
# ----------------------------
SYSTEM_PROMPT = """
You are a Tier 2 IT support engineer.

Rules:
- Be concise
- Be action-focused
- Ask minimal questions
- Prefer steps over explanations
"""

# ----------------------------
# HOME
# ----------------------------
@app.route("/")
def home():
    return render_template("index.html")

# ----------------------------
# MAIN CHAT ENDPOINT
# ----------------------------
@app.route("/ask", methods=["POST"])
def ask():
    data = request.json
    user_input = data.get("message", "")
    session_id = data.get("session_id")

    # ----------------------------
    # RESTORE OR CREATE SESSION
    # ----------------------------
    if not session_id or session_id not in sessions:
        session_id = str(uuid.uuid4())
        sessions[session_id] = {
            "messages": [],
            "active_flow": None,
            "step": 0,
            "issue_type": None
        }

    session = sessions[session_id]

    session["messages"].append({"role": "user", "content": user_input})

    # ----------------------------
    # DETECT ISSUE (ONLY IF NOT IN FLOW)
    # ----------------------------
    detected = detect_issue(user_input)

    if session["active_flow"] is None:
        session["issue_type"] = detected

        if detected in PLAYBOOKS:
            session["active_flow"] = detected
            session["step"] = 0

    # ----------------------------
    # IF IN PLAYBOOK MODE
    # ----------------------------
    if session["active_flow"]:
        flow = PLAYBOOKS[session["active_flow"]]

        if session["step"] < len(flow):
            reply = flow[session["step"]]
            session["step"] += 1
        else:
            reply = "Troubleshooting complete. What is the result now?"
            session["active_flow"] = None

    # ----------------------------
    # FALLBACK AI MODE
    # ----------------------------
    else:
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT}
        ]
        messages.extend(session["messages"][-6:])

        response = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=messages,
            max_tokens=400,
            temperature=0.3
        )

        reply = response.choices[0].message.content

    session["messages"].append({"role": "assistant", "content": reply})

    return jsonify({
        "session_id": session_id,
        "response": reply,
        "issue_type": session["issue_type"],
        "active_flow": session["active_flow"]
    })


# ----------------------------
# RUN
# ----------------------------
if __name__ == "__main__":
    app.run(debug=True)
