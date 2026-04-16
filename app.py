import os
import uuid
from flask import Flask, request, jsonify, session, redirect, render_template

app = Flask(__name__)

# ----------------------------
# CORE CONFIG
# ----------------------------
app.secret_key = os.getenv("SECRET_KEY", "dev-secret")

app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_SECURE"] = True

# ----------------------------
# IN-MEMORY STORAGE (BETA MODE)
# ----------------------------
USERS = {}         # email -> {password, is_admin}
INVITES = set()    # valid invite codes
SESSIONS = {}      # session tracking

# create default admin
USERS["admin@local"] = {
    "password": "admin",
    "is_admin": True
}

# ----------------------------
# HEALTH CHECK
# ----------------------------
@app.route("/health")
def health():
    return jsonify({
        "status": "ok",
        "users": len(USERS),
        "active_sessions": len(SESSIONS)
    })

# ----------------------------
# HOME
# ----------------------------
@app.route("/")
def home():
    return render_template("index.html")

# ----------------------------
# DASHBOARD
# ----------------------------
@app.route("/dashboard")
def dashboard():
    if not session.get("user"):
        return redirect("/")
    return render_template("dashboard.html")

# ----------------------------
# SIGNUP (INVITE REQUIRED)
# ----------------------------
@app.route("/signup", methods=["POST"])
def signup():

    data = request.json

    email = data.get("email", "").strip()
    password = data.get("password", "").strip()
    invite = data.get("invite_code", "").strip()

    if not email or not password:
        return jsonify({"error": "missing fields"}), 400

    if invite not in INVITES:
        return jsonify({"error": "invalid invite"}), 403

    if email in USERS:
        return jsonify({"error": "user exists"}), 400

    USERS[email] = {
        "password": password,
        "is_admin": False
    }

    INVITES.remove(invite)

    return jsonify({"status": "created"})

# ----------------------------
# LOGIN (FIXED SESSION)
# ----------------------------
@app.route("/login", methods=["POST"])
def login():

    data = request.json
    email = data.get("email", "")
    password = data.get("password", "")

    user = USERS.get(email)

    if not user or user["password"] != password:
        return jsonify({"error": "invalid login"}), 401

    session["user"] = email
    session.modified = True

    return jsonify({"status": "ok"})

# ----------------------------
# LOGOUT
# ----------------------------
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

# ----------------------------
# ASK (COPILOT ENGINE SIMPLIFIED)
# ----------------------------
@app.route("/ask", methods=["POST"])
def ask():

    if not session.get("user"):
        return jsonify({"error": "unauthorized"}), 401

    data = request.json
    msg = data.get("message", "").lower()

    if "vpn" in msg:
        step = "Check VPN connection → reconnect VPN client"
    elif "outlook" in msg:
        step = "Restart Outlook → run in safe mode if needed"
    elif "login" in msg:
        step = "Verify password → check account lock status"
    elif "crash" in msg:
        step = "Check Task Manager → CPU/RAM usage"
    else:
        step = "Restart device → check issue again"

    return jsonify({
        "issue_detected": True,
        "step": step
    })

# ----------------------------
# ANALYTICS (FIXED BEHAVIOR)
# ----------------------------
@app.route("/analytics")
def analytics():

    if not session.get("user"):
        return redirect("/")

    user = session.get("user")

    return jsonify({
        "current_user": user,
        "total_users": len(USERS),
        "active_sessions": len(SESSIONS)
    })

# ----------------------------
# ADMIN: CREATE INVITE
# ----------------------------
@app.route("/admin/invite")
def create_invite():

    user = session.get("user")

    if user != "admin@local":
        return "forbidden", 403

    code = str(uuid.uuid4())[:8]
    INVITES.add(code)

    return jsonify({"invite": code})

# ----------------------------
# INIT
# ----------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
