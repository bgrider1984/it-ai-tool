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

def detect_issue(text):
    t = text.lower()

    rules = {
        "outlook": ["outlook", "email", "mail", "exchange"],
        "vpn": ["vpn", "dns", "network", "internet", "wifi"],
        "login": ["login", "password", "sign in", "locked out"],
        "printer": ["printer", "print"],
        "software": ["crash", "freeze", "not responding"],
        "performance": ["slow", "lag"]
    }

    for k, v in rules.items():
        if any(x in t for x in v):
            return k

    return "general"

PLAYBOOKS = {
    "outlook": [
        "Step 1: Press Windows + R",
        "Step 2: Type outlook.exe /safe",
        "Step 3: Press Enter",
        "Step 4: Tell me what happens"
    ],
    "vpn": [
        "Step 1: Press Windows + R",
        "Step 2: Type ncpa.cpl",
        "Step 3: Disable and re-enable adapter",
        "Step 4: Test connection"
    ],
    "login": [
        "Step 1: Check Caps Lock",
        "Step 2: Re-enter credentials",
        "Step 3: Try password reset if needed"
    ]
}

SYSTEM_PROMPT = """
You are a Tier 2 IT support engineer.
Be concise, direct, and action-focused.
"""

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
            "messages": [],
            "active_flow": None,
            "step": 0
        }

    session = sessions[session_id]

    session["messages"].append({"role": "user", "content": user_input})

    issue = detect_issue(user_input)

    if issue in PLAYBOOKS and session["active_flow"] is None:
        session["active_flow"] = issue
        session["step"] = 0

    if session["active_flow"]:
        flow = PLAYBOOKS[session["active_flow"]]

        if session["step"] < len(flow):
            reply = flow[session["step"]]
            session["step"] += 1
        else:
            reply = "Done. What do you see now?"
            session["active_flow"] = None
    else:
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
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
        "issue_type": issue
    })


if __name__ == "__main__":
    app.run(debug=True)
