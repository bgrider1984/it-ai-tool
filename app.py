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
# MULTI-STEP TREE PLAYBOOKS
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
                "message": "Disable all add-ins (File → Options → Add-ins → COM Add-ins → Go). Restart Outlook normally.",
                "end": True
            },
            "error_check": {
                "question": "Do you see an error message?",
                "yes": "error_specific",
                "no": "new_profile"
            },
            "error_specific": {
                "message": "Capture the exact error message and search internal KB or Microsoft docs for targeted fix.",
                "end": True
            },
            "new_profile": {
                "message": "Create a new Outlook profile (Control Panel → Mail → Show Profiles → Add).",
                "end": True
            }
        }
    },

    "vpn": {
        "start": "reset_adapter",
        "nodes": {
            "reset_adapter": {
                "question": "Reset network adapter (ncpa.cpl). Did connection return?",
                "yes": "resolved",
                "no": "dns"
            },
            "dns": {
                "message": "Run Command Prompt as admin → ipconfig /flushdns",
                "end": True
            },
            "resolved": {
                "message": "Connection restored. Monitor stability.",
                "end": True
            }
        }
    }
}

# ----------------------------
# SYSTEM PROMPT (AI FALLBACK)
# ----------------------------
SYSTEM_PROMPT = """
You are a Tier 2 IT engineer.

Be:
- concise
- diagnostic
- adaptive
"""

@app.route("/")
def home():
    return render_template("index.html")

# ----------------------------
# MAIN CHAT
# ----------------------------
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
    # HANDLE TREE LOGIC
    # ----------------------------
    if issue in PLAYBOOKS and session["node"]:

        tree = PLAYBOOKS[issue]["nodes"]
        current_node = tree[session["node"]]

        # If user answering a question
        if "question" not in current_node:

            # move forward if message node
            if current_node.get("end"):
                session["node"] = None
                return jsonify({
                    "session_id": session_id,
                    "response": current_node["message"]
                })

        # If question node
        if "question" in current_node:

            # If user already answered
            if any(x in user_text for x in ["yes", "no"]):
                if "yes" in user_text:
                    next_node = current_node["yes"]
                else:
                    next_node = current_node["no"]

                session["node"] = next_node
                next_data = tree[next_node]

                if "message" in next_data:
                    session["node"] = None
                    return jsonify({
                        "session_id": session_id,
                        "response": next_data["message"]
                    })

                return jsonify({
                    "session_id": session_id,
                    "response": next_data["question"]
                })

            # Ask the question
            return jsonify({
                "session_id": session_id,
                "response": current_node["question"]
            })

    # ----------------------------
    # AI FALLBACK
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

    return jsonify({
        "session_id": session_id,
        "response": response.choices[0].message.content
    })


if __name__ == "__main__":
    app.run(debug=True)
