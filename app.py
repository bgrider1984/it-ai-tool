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
# TREE PLAYBOOKS
# ----------------------------
PLAYBOOKS = {
    "outlook": {
        "start": "safe_mode",
        "nodes": {
            "safe_mode": {
                "question": "Open Outlook in Safe Mode (Win+R → outlook.exe /safe). Did it open?",
                "yes": "disable_addins",
                "no": "error_check"
            },
            "disable_addins": {
                "message": "Disable all add-ins and restart Outlook normally.",
                "end": True
            },
            "error_check": {
                "question": "Do you see an error message?",
                "yes": "error_specific",
                "no": "new_profile"
            },
            "error_specific": {
                "message": "Capture the exact error and check Microsoft docs.",
                "end": True
            },
            "new_profile": {
                "message": "Create a new Outlook profile.",
                "end": True
            }
        }
    }
}

# ----------------------------
# AI DYNAMIC TROUBLESHOOTING
# ----------------------------
def ai_next_step(issue, history):
    prompt = f"""
You are a Tier 2 IT engineer continuing troubleshooting.

Issue: {issue}

Previous steps taken:
{history}

Provide:
- The next best troubleshooting step
- Be concise
- Do NOT repeat previous steps
- If needed, ask ONE focused question
"""

    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=200,
        temperature=0.3
    )

    return response.choices[0].message.content

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
            "issue": None,
            "node": None,
            "history": []
        }

    session = sessions[session_id]
    session["history"].append(user_input)

    user_text = user_input.lower()

    # ----------------------------
    # DETECT ISSUE
    # ----------------------------
    if session["issue"] is None:
        session["issue"] = detect_issue(user_input)

        if session["issue"] in PLAYBOOKS:
            session["node"] = PLAYBOOKS[session["issue"]]["start"]

    issue = session["issue"]

    # ----------------------------
    # TREE LOGIC
    # ----------------------------
    if issue in PLAYBOOKS and session["node"]:
        tree = PLAYBOOKS[issue]["nodes"]
        current = tree[session["node"]]

        # QUESTION NODE
        if "question" in current:

            if "yes" in user_text or "no" in user_text:
                next_node = current["yes"] if "yes" in user_text else current["no"]
                session["node"] = next_node

                next_data = tree[next_node]

                if next_data.get("end"):
                    session["node"] = None

                    # 🔥 AI CONTINUES AFTER TREE ENDS
                    ai_reply = ai_next_step(issue, session["history"])

                    return jsonify({
                        "session_id": session_id,
                        "response": next_data["message"] + "\n\n" + ai_reply
                    })

                return jsonify({
                    "session_id": session_id,
                    "response": next_data.get("question", next_data.get("message"))
                })

            return jsonify({
                "session_id": session_id,
                "response": current["question"]
            })

        # MESSAGE NODE
        if current.get("end"):
            session["node"] = None

            ai_reply = ai_next_step(issue, session["history"])

            return jsonify({
                "session_id": session_id,
                "response": current["message"] + "\n\n" + ai_reply
            })

    # ----------------------------
    # FULL AI MODE
    # ----------------------------
    ai_reply = ai_next_step(issue, session["history"])

    return jsonify({
        "session_id": session_id,
        "response": ai_reply
    })


if __name__ == "__main__":
    app.run(debug=True)
