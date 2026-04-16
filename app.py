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
# ISSUE DETECTION
# ----------------------------
def detect_issue(text):
    t = text.lower()

    if "outlook" in t:
        return "outlook"
    if "vpn" in t or "network" in t:
        return "vpn"
    if "login" in t or "password" in t:
        return "login"

    return "general"

# ----------------------------
# ADAPTIVE PLAYBOOKS
# ----------------------------
PLAYBOOKS = {
    "outlook": {
        "steps": [
            {
                "ask": "Open Outlook in Safe Mode (Win+R → outlook.exe /safe). Did it open?",
                "yes": "Add-in issue. Disable all add-ins and restart Outlook normally.",
                "no": "Possible profile issue. Create a new Outlook profile via Control Panel."
            }
        ]
    },
    "vpn": {
        "steps": [
            {
                "ask": "Reset your network adapter. Did the connection restore?",
                "yes": "Network adapter issue resolved.",
                "no": "Flush DNS (ipconfig /flushdns) and retry VPN."
            }
        ]
    }
}

SYSTEM_PROMPT = """
You are a Tier 2 IT engineer.

Rules:
- Be concise
- Diagnose based on user feedback
- Do NOT repeat steps
- Adapt based on results
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
            "issue": None,
            "step": 0,
            "history": [],
            "awaiting_answer": False
        }

    session = sessions[session_id]

    user_text = user_input.lower()
    session["history"].append(user_input)

    # ----------------------------
    # DETECT ISSUE
    # ----------------------------
    if session["issue"] is None:
        session["issue"] = detect_issue(user_input)

    issue = session["issue"]

    # ----------------------------
    # HANDLE PLAYBOOK
    # ----------------------------
    if issue in PLAYBOOKS:

        step_data = PLAYBOOKS[issue]["steps"][0]

        # If waiting for yes/no answer
        if session["awaiting_answer"]:
            session["awaiting_answer"] = False

            if "yes" in user_text:
                reply = step_data["yes"]
            elif "no" in user_text:
                reply = step_data["no"]
            else:
                reply = "Please answer yes or no."

            return jsonify({
                "session_id": session_id,
                "response": reply
            })

        # Ask question
        session["awaiting_answer"] = True

        return jsonify({
            "session_id": session_id,
            "response": step_data["ask"]
        })

    # ----------------------------
    # AI FALLBACK (ADAPTIVE)
    # ----------------------------
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": "\n".join(session["history"][-5:])}
    ]

    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=messages,
        max_tokens=300,
        temperature=0.3
    )

    reply = response.choices[0].message.content

    return jsonify({
        "session_id": session_id,
        "response": reply
    })


if __name__ == "__main__":
    app.run(debug=True)
