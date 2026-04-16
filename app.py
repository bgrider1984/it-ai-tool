import os
import uuid
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

sessions = {}

# ----------------------------
# ISSUE DETECTION (NO STICKY GENERAL LOOP)
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
    if "crash" in t or "freez" in t:
        return "system_crash"

    return "unknown"

# ----------------------------
# SMART TROUBLESHOOTING ENGINE
# ----------------------------
def get_next_step(issue, repeat_count):
    if issue == "outlook":
        steps = [
            "Check if Outlook is running in Safe Mode.",
            "Disable add-ins and retry launch.",
            "Rebuild Outlook profile."
        ]
    elif issue == "vpn":
        steps = [
            "Check VPN adapter status.",
            "Flush DNS cache and retry connection.",
            "Reinstall VPN client."
        ]
    elif issue == "hardware_overheating":
        steps = [
            "Check CPU usage and running processes.",
            "Inspect fan operation and airflow.",
            "Consider thermal paste or hardware issue."
        ]
    elif issue == "system_crash":
        steps = [
            "Check recent software changes or updates.",
            "Boot into Safe Mode and test stability.",
            "Check Event Viewer for crash logs."
        ]
    else:
        steps = [
            "Gather more details about the issue.",
            "Check system performance and error patterns.",
            "Run basic system diagnostics before escalation."
        ]

    # ESCALATION LOGIC
    if repeat_count >= len(steps):
        return "Escalation required: issue likely deeper system or hardware level."

    return steps[repeat_count]

# ----------------------------
# RESET DETECTION (INTENT SWITCH)
# ----------------------------
def is_new_issue(prev, new):
    triggers = ["new issue", "actually", "different", "instead", "switching", "forget"]
    return prev is None or any(t in new.lower() for t in triggers)

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
            "last_issue": None,
            "repeat_count": 0
        }

    session = sessions[session_id]

    issue = detect_issue(message)

    # ----------------------------
    # INTENT SWITCH RESET
    # ----------------------------
    if is_new_issue(session["last_issue"], message) or session["last_issue"] != issue:
        session["repeat_count"] = 0
        session["last_issue"] = issue
    else:
        session["repeat_count"] += 1

    # ----------------------------
    # GET NEXT STEP
    # ----------------------------
    response = get_next_step(issue, session["repeat_count"])

    return jsonify({
        "session_id": session_id,
        "response": response,
        "issue": issue,
        "step": session["repeat_count"]
    })


if __name__ == "__main__":
    app.run(debug=True)
