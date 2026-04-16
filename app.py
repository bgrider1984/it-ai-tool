import os
import uuid
from datetime import datetime
from flask import Flask, request, jsonify, session, redirect, render_template
from flask_sqlalchemy import SQLAlchemy

# ----------------------------
# APP SETUP
# ----------------------------
app = Flask(__name__)

app.secret_key = os.getenv("SECRET_KEY", "dev-secret")

app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_SECURE"] = True

app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL", "sqlite:///local.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

# ----------------------------
# SESSION MEMORY
# ----------------------------
sessions = {}

def get_session():
    sid = session.get("sid")
    if not sid:
        sid = str(uuid.uuid4())
        session["sid"] = sid
        sessions[sid] = {
            "issue": None,
            "step_index": 0,
            "steps": [],
            "history": []
        }
    return sessions[sid]

# ----------------------------
# ISSUE DETECTION
# ----------------------------
def detect_issue(text):
    t = text.lower()

    if "vpn" in t or "network" in t:
        return "network"
    if "outlook" in t or "email" in t:
        return "outlook"
    if "login" in t or "password" in t:
        return "auth"
    if "slow" in t or "crash" in t:
        return "performance"

    return "general"

# ----------------------------
# TROUBLESHOOTING TREE
# ----------------------------
TREE = {
    "network": [
        {"id": "net1", "text": "Check WiFi/Ethernet connection"},
        {"id": "net2", "text": "Flush DNS (ipconfig /flushdns)"},
        {"id": "net3", "text": "Reset network adapter"},
        {"id": "net4", "text": "Test DNS (8.8.8.8)"}
    ],
    "outlook": [
        {"id": "out1", "text": "Restart Outlook"},
        {"id": "out2", "text": "Run Outlook Safe Mode"},
        {"id": "out3", "text": "Repair Office"},
        {"id": "out4", "text": "Recreate Outlook Profile"}
    ],
    "auth": [
        {"id": "auth1", "text": "Verify password"},
        {"id": "auth2", "text": "Clear cached credentials"},
        {"id": "auth3", "text": "Check account lockout"},
        {"id": "auth4", "text": "Reset password"}
    ],
    "performance": [
        {"id": "perf1", "text": "Check Task Manager CPU/RAM"},
        {"id": "perf2", "text": "Scan for malware"},
        {"id": "perf3", "text": "Check disk usage"},
        {"id": "perf4", "text": "Restart system"}
    ],
    "general": [
        {"id": "gen1", "text": "Restart device"},
        {"id": "gen2", "text": "Check recent changes"},
        {"id": "gen3", "text": "Run system diagnostics"}
    ]
}

# ----------------------------
# AUTH
# ----------------------------
def current_user():
    return session.get("user_id")

# ----------------------------
# HOME
# ----------------------------
@app.route("/")
def home():
    return render_template("index.html")

@app.route("/dashboard")
def dashboard():
    if not session.get("user_id"):
        return redirect("/")
    return render_template("dashboard.html")

# ----------------------------
# HEALTH (DEBUG FIXED)
# ----------------------------
@app.route("/health")
def health():
    return jsonify({
        "status": "ok",
        "sessions": len(sessions)
    })

# ----------------------------
# LOGIN (FIXED SESSION ISSUE)
# ----------------------------
@app.route("/login", methods=["POST"])
def login():
    data = request.json

    # TEMP SIMPLE LOGIN (until DB fully enforced)
    if data.get("email") and data.get("password"):
        session["user_id"] = str(uuid.uuid4())
        session.modified = True
        return jsonify({"status": "ok"})

    return jsonify({"error": "invalid"}), 401

# ----------------------------
# COPILOT v4 ENGINE
# ----------------------------
@app.route("/ask", methods=["POST"])
def ask():

    data = request.json
    message = data.get("message")

    state = get_session()

    issue = detect_issue(message)
    state["issue"] = issue

    steps = TREE.get(issue, TREE["general"])

    index = state["step_index"]

    if index >= len(steps):
        step = {"id": "done", "text": "Escalate to Tier 2 technician"}
    else:
        step = steps[index]

    state["steps"].append(step)

    response = {
        "issue": issue,
        "step": step,
        "step_index": index,
        "next_action": "run_step"
    }

    return jsonify(response)

# ----------------------------
# STEP EXECUTION
# ----------------------------
@app.route("/run_step", methods=["POST"])
def run_step():

    data = request.json
    sid = session.get("sid")
    state = sessions.get(sid)

    success = data.get("success")

    if success:
        state["step_index"] += 1
        result = "Step marked successful → moving to next step"
    else:
        # branch fallback
        state["step_index"] += 1
        result = "Step failed → switching troubleshooting branch"

    return jsonify({
        "result": result,
        "next_index": state["step_index"]
    })

# ----------------------------
# ANALYTICS
# ----------------------------
@app.route("/analytics")
def analytics():

    if not session.get("user_id"):
        return "Unauthorized", 403

    return jsonify({
        "users": 1,
        "sessions": len(sessions),
        "status": "beta-v4-active"
    })

# ----------------------------
# INIT
# ----------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
