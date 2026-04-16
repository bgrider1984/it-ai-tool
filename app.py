import os
import uuid
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

sessions = {}

# ----------------------------
# ISSUE DETECTION
# ----------------------------
def detect_issue(text):
    t = text.lower()

    if "outlook" in t:
        return "outlook"
    if "vpn" in t:
        return "vpn"
    if "login" in t or "password" in t:
        return "auth"
    if "hot" in t or "overheating" in t:
        return "hardware_overheating"
    if "crash" in t or "freeze" in t or "lag" in t:
        return "system_instability"

    return "unknown"

# ----------------------------
# DIAGNOSTIC INTELLIGENCE MODEL
# ----------------------------
def diagnostic_model(issue, state):
    """
    state contains:
    - attempt_count
    - failed_paths
    """

    attempt = state["attempt_count"]
    failed = state["failed_paths"]

    # base reasoning profiles
    profiles = {
        "outlook": {
            "software": 0.8,
            "config": 0.7,
            "hardware": 0.1,
            "steps": [
                ("safe_mode", "Start Outlook in Safe Mode"),
                ("addins", "Disable Outlook Add-ins"),
                ("profile", "Rebuild Outlook Profile")
            ]
        },

        "vpn": {
            "software": 0.6,
            "config": 0.8,
            "hardware": 0.1,
            "steps": [
                ("adapter", "Check network adapter"),
                ("dns", "Flush DNS cache"),
                ("reinstall", "Reinstall VPN client")
            ]
        },

        "hardware_overheating": {
            "software": 0.3,
            "config": 0.2,
            "hardware": 0.9,
            "steps": [
                ("process", "Check CPU usage"),
                ("fans", "Inspect fan operation"),
                ("thermal", "Check thermal paste / hardware health")
            ]
        },

        "system_instability": {
            "software": 0.6,
            "config": 0.4,
            "hardware": 0.6,
            "steps": [
                ("updates", "Check recent updates"),
                ("safe_boot", "Boot into Safe Mode"),
                ("event_viewer", "Check system crash logs")
            ]
        },

        "unknown": {
            "software": 0.5,
            "config": 0.5,
            "hardware": 0.5,
            "steps": [
                ("gather", "Gather more detailed symptoms"),
                ("isolate", "Isolate when issue occurs"),
                ("diagnose", "Run full system diagnostics")
            ]
        }
    }

    profile = profiles.get(issue, profiles["unknown"])

    steps = profile["steps"]

    # remove failed steps from priority
    for f in failed:
        steps = [s for s in steps if s[0] != f]

    if attempt >= len(steps):
        return {
            "message": "Escalation required: deeper system-level diagnosis needed.",
            "step": None
        }

    step = steps[attempt]

    return {
        "message": step[1],
        "step": step[0],
        "confidence": profile
    }

# ----------------------------
# INTENT SWITCH DETECTION
# ----------------------------
def is_new_issue(prev, message):
    triggers = ["new issue", "actually", "different", "instead", "switch", "forget"]
    if prev is None:
        return True
    return any(t in message.lower() for t in triggers)

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

    if not session_id or session_id not in sessions:
        session_id = str(uuid.uuid4())
        sessions[session_id] = {
            "issue": None,
            "attempt_count": 0,
            "last_message": None,
            "failed_paths": []
        }

    session = sessions[session_id]

    issue = detect_issue(message)

    # ----------------------------
    # INTENT SWITCH RESET
    # ----------------------------
    if is_new_issue(session["last_message"], message) or issue != session["issue"]:
        session["attempt_count"] = 0
        session["failed_paths"] = []
        session["issue"] = issue
    else:
        session["attempt_count"] += 1

    session["last_message"] = message

    # ----------------------------
    # DIAGNOSTIC RESPONSE
    # ----------------------------
    result = diagnostic_model(issue, session)

    return jsonify({
        "session_id": session_id,
        "response": result["message"],
        "step": session["attempt_count"],
        "issue": issue
    })


if __name__ == "__main__":
    app.run(debug=True)
