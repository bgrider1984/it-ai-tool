import os
import uuid
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

# ----------------------------
# SESSIONS
# ----------------------------
sessions = {}

# ----------------------------
# ISSUE DETECTION (CURRENT MESSAGE ONLY)
# ----------------------------
def detect_issue(text):
    t = text.lower()

    if "outlook" in t:
        return "outlook"
    if "vpn" in t:
        return "vpn"
    if "login" in t:
        return "auth"
    if "hot" in t or "overheating" in t or "heat" in t:
        return "hardware_overheating"

    return "general"

# ----------------------------
# INTENT SWITCH DETECTION (NEW)
# ----------------------------
def detect_intent_switch(prev_text, new_text):
    if not prev_text:
        return False

    triggers = [
        "new issue",
        "different issue",
        "actually",
        "instead",
        "switching",
        "forget that",
        "not that"
    ]

    new_lower = new_text.lower()

    return any(t in new_lower for t in triggers)

# ----------------------------
# RESET SESSION STATE
# ----------------------------
def reset_session(session):
    session["history"] = []
    session["current_issue"] = None
    session["failed_fixes"] = []

# ----------------------------
# SIMPLE FIX ENGINE (PLACEHOLDER FOR NOW)
# ----------------------------
def get_fixes(issue):
    if issue == "outlook":
        return [
            {"name": "safe_mode", "label": "Start Outlook Safe Mode", "confidence": "High"},
            {"name": "restart_outlook", "label": "Restart Outlook Process", "confidence": "Medium"}
        ]

    if issue == "hardware_overheating":
        return [
            {"name": "check_fans", "label": "Check Fan Operation", "confidence": "High"},
            {"name": "close_apps", "label": "Reduce CPU Load", "confidence": "Medium"}
        ]

    return [
        {"name": "basic_restart", "label": "Restart Device", "confidence": "High"}
    ]

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

    # ----------------------------
    # INIT SESSION
    # ----------------------------
    if not session_id or session_id not in sessions:
        session_id = str(uuid.uuid4())
        sessions[session_id] = {
            "history": [],
            "current_issue": None,
            "last_message": None,
            "failed_fixes": []
        }

    session = sessions[session_id]

    # ----------------------------
    # INTENT SWITCH CHECK
    # ----------------------------
    switch = detect_intent_switch(session.get("last_message"), message)

    if switch:
        reset_session(session)
        response_prefix = "🔄 New issue detected — resetting context.\n\n"
    else:
        response_prefix = ""

    session["last_message"] = message
    session["history"].append(message)

    # ----------------------------
    # DETECT ISSUE (ONLY FROM CURRENT MESSAGE)
    # ----------------------------
    issue = detect_issue(message)
    session["current_issue"] = issue

    # ----------------------------
    # GENERATE FIXES
    # ----------------------------
    fixes = get_fixes(issue)

    response = response_prefix + f"Detected issue: {issue}"

    return jsonify({
        "session_id": session_id,
        "response": response,
        "fixes": fixes
    })


if __name__ == "__main__":
    app.run(debug=True)
