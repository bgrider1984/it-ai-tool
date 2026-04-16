import os
import uuid
from datetime import datetime
from flask import Flask, request, jsonify, session, redirect, render_template
from flask_sqlalchemy import SQLAlchemy
from openai import OpenAI

# ----------------------------
# APP SETUP
# ----------------------------
app = Flask(__name__)

app.secret_key = os.getenv("SECRET_KEY", "dev-secret-change-me")

app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_SECURE"] = True

app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL", "sqlite:///local.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

# ----------------------------
# OPENAI
# ----------------------------
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY")) if os.getenv("OPENAI_API_KEY") else None

# ----------------------------
# MODELS
# ----------------------------
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True)
    password = db.Column(db.String(120))
    is_admin = db.Column(db.Boolean, default=False)

class Invite(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(50), unique=True)
    used = db.Column(db.Boolean, default=False)

class ChatLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer)
    message = db.Column(db.Text)
    response = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# ----------------------------
# SESSION TROUBLESHOOTING MEMORY
# ----------------------------
sessions = {}

def get_session():
    sid = session.get("sid")
    if not sid:
        sid = str(uuid.uuid4())
        session["sid"] = sid
        sessions[sid] = {
            "issue": None,
            "steps": [],
            "history": []
        }
    return sessions[sid]

# ----------------------------
# ISSUE DETECTION ENGINE
# ----------------------------
def detect_issue(text):
    t = text.lower()

    if any(x in t for x in ["vpn", "network", "internet"]):
        return "network"
    if "outlook" in t or "email" in t:
        return "outlook"
    if "login" in t or "password" in t:
        return "auth"
    if "slow" in t or "crash" in t or "freeze" in t:
        return "performance"

    return "general"

# ----------------------------
# TROUBLESHOOTING TREE ENGINE
# ----------------------------
def next_step(issue, state):

    tree = {
        "network": [
            "Check WiFi / Ethernet connection",
            "Run ipconfig /flushdns",
            "Reset network adapter",
            "Test DNS (8.8.8.8)"
        ],
        "outlook": [
            "Check Outlook is running",
            "Restart Outlook in safe mode",
            "Repair Office installation",
            "Recreate Outlook profile"
        ],
        "auth": [
            "Verify password",
            "Reset cached credentials",
            "Check AD lockout status",
            "Reset password"
        ],
        "performance": [
            "Check Task Manager CPU/RAM",
            "Scan for malware",
            "Check disk usage",
            "Restart system"
        ],
        "general": [
            "Restart device",
            "Check recent changes",
            "Run system diagnostics"
        ]
    }

    steps = tree.get(issue, tree["general"])

    done = state["steps"]

    for step in steps:
        if step not in done:
            return step

    return "Escalate to Tier 2 support"

# ----------------------------
# AUTH HELPERS
# ----------------------------
def current_user():
    uid = session.get("user_id")
    return User.query.get(uid) if uid else None

def is_admin():
    u = current_user()
    return u and u.is_admin

# ----------------------------
# ROUTES
# ----------------------------
@app.route("/")
def home():
    return render_template("index.html") if not session.get("user_id") else redirect("/dashboard")

@app.route("/dashboard")
def dashboard():
    if not session.get("user_id"):
        return redirect("/")
    return render_template("dashboard.html")

# ----------------------------
# HEALTH
# ----------------------------
@app.route("/health")
def health():
    return jsonify({
        "status": "ok",
        "sessions": len(sessions)
    })

# ----------------------------
# LOGIN
# ----------------------------
@app.route("/login", methods=["POST"])
def login():

    data = request.json
    user = User.query.filter_by(
        email=data.get("email"),
        password=data.get("password")
    ).first()

    if not user:
        return jsonify({"error": "invalid login"}), 401

    session["user_id"] = user.id
    session.modified = True

    return jsonify({"status": "ok"})

# ----------------------------
# CHAT + AI TROUBLESHOOTING v3
# ----------------------------
@app.route("/ask", methods=["POST"])
def ask():

    user = current_user()
    if not user:
        return jsonify({"error": "unauthorized"}), 401

    data = request.json
    message = data.get("message")

    state = get_session()

    issue = detect_issue(message)
    state["issue"] = issue
    state["history"].append(message)

    step = next_step(issue, state)
    state["steps"].append(step)

    response = f"""
🔍 Issue Type: {issue}

🧠 Next Step:
{step}

👉 Try this and tell me the result (worked / failed)
"""

    db.session.add(ChatLog(
        user_id=user.id,
        message=message,
        response=response
    ))

    db.session.commit()

    return jsonify({
        "response": response,
        "issue": issue,
        "step": step
    })

# ----------------------------
# ANALYTICS
# ----------------------------
@app.route("/analytics")
def analytics():

    if not is_admin():
        return "Unauthorized", 403

    return jsonify({
        "users": User.query.count(),
        "messages": ChatLog.query.count(),
        "active_sessions": len(sessions)
    })

# ----------------------------
# ADMIN INVITE
# ----------------------------
@app.route("/admin/invite", methods=["POST"])
def invite():

    if not is_admin():
        return "forbidden", 403

    code = str(uuid.uuid4())[:8]

    db.session.add(Invite(code=code))
    db.session.commit()

    return jsonify({"invite": code})

# ----------------------------
# INIT
# ----------------------------
if __name__ == "__main__":
    with app.app_context():
        db.create_all()

        if not User.query.filter_by(is_admin=True).first():
            db.session.add(User(
                email="admin@local",
                password="admin",
                is_admin=True
            ))
            db.session.commit()

    app.run(host="0.0.0.0", port=10000)
