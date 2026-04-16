import os
import uuid
from datetime import datetime
from flask import Flask, request, jsonify, session, redirect, render_template
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)

app.secret_key = os.getenv("SECRET_KEY", "dev-secret")

app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_SECURE"] = True

app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL", "sqlite:///local.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

# ----------------------------
# USERS (BETA SIMPLE)
# ----------------------------
USERS = {
    "admin@local": {"password": "admin", "is_admin": True}
}

INVITES = set()
SESSION_INDEX = {}

# ----------------------------
# CHAT HISTORY MODEL
# ----------------------------
class ChatHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user = db.Column(db.String(120))
    role = db.Column(db.String(20))
    message = db.Column(db.Text)
    session_id = db.Column(db.String(80))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

# ----------------------------
# SESSION MEMORY
# ----------------------------
sessions = {}

def get_session():
    sid = session.get("sid")

    if not sid:
        sid = str(uuid.uuid4())
        session["sid"] = sid
        sessions[sid] = {"history": []}

    return sid

# ----------------------------
# INTENT CLASSIFIER (NEW CORE LOGIC)
# ----------------------------
def classify_intent(message):
    t = message.lower()

    vague_keywords = [
        "won't open",
        "not working",
        "doesn't work",
        "broken",
        "issue",
        "problem",
        "won’t start",
        "cannot open"
    ]

    specific_keywords = [
        "error code",
        "blue screen",
        "crash dump",
        "vpn error",
        "outlook error",
        "exception"
    ]

    if any(k in t for k in vague_keywords):
        return "clarify"

    if any(k in t for k in specific_keywords):
        return "direct_fix"

    return "clarify"

# ----------------------------
# ROUTES
# ----------------------------
@app.route("/")
def home():
    return render_template("index.html")

@app.route("/dashboard")
def dashboard():
    if not session.get("user"):
        return redirect("/")
    return render_template("dashboard.html")

# ----------------------------
# LOGIN
# ----------------------------
@app.route("/login", methods=["POST"])
def login():
    data = request.json

    user = USERS.get(data.get("email"))

    if not user or user["password"] != data.get("password"):
        return jsonify({"error": "invalid login"}), 401

    session["user"] = data.get("email")
    session.modified = True

    return jsonify({"status": "ok"})

# ----------------------------
# ASK (FIXED LOGIC — NO BAD FALLBACKS)
# ----------------------------
@app.route("/ask", methods=["POST"])
def ask():

    if not session.get("user"):
        return jsonify({"error": "unauthorized"}), 401

    data = request.json
    message = data.get("message", "")

    sid = get_session()

    # save session index
    if sid not in SESSION_INDEX:
        SESSION_INDEX[sid] = {
            "title": message[:30],
            "created": str(datetime.utcnow())
        }

    intent = classify_intent(message)

    # ----------------------------
    # CRITICAL FIX: PROPER FLOW CONTROL
    # ----------------------------
    if intent == "clarify":
        reply = (
            "Before I suggest fixes, I need a bit more detail:\n\n"
            "1. Is this happening to ALL applications or just one?\n"
            "2. Did this start after a restart or update?\n"
            "3. Can you open Task Manager (Ctrl + Shift + Esc)?"
        )

    else:
        msg = message.lower()

        if "vpn" in msg:
            reply = "Step 1: Reconnect VPN client → Step 2: Verify internet access"
        elif "outlook" in msg:
            reply = "Step 1: Restart Outlook → Step 2: Safe Mode test"
        elif "crash" in msg:
            reply = "Step 1: Check CPU/RAM usage in Task Manager"
        elif "slow" in msg:
            reply = "Step 1: Check disk usage → Step 2: Disable background apps"
        else:
            reply = "Start with a system restart, then re-test the issue."

    # SAVE CHAT
    db.session.add(ChatHistory(
        user=session["user"],
        role="user",
        message=message,
        session_id=sid
    ))

    db.session.add(ChatHistory(
        user=session["user"],
        role="assistant",
        message=reply,
        session_id=sid
    ))

    db.session.commit()

    return jsonify({
        "response": reply,
        "session_id": sid
    })

# ----------------------------
# SESSION LIST
# ----------------------------
@app.route("/sessions")
def sessions_list():

    if not session.get("user"):
        return jsonify({"error": "unauthorized"}), 401

    return jsonify([
        {
            "session_id": sid,
            "title": data["title"],
            "created": data["created"]
        }
        for sid, data in SESSION_INDEX.items()
    ])

# ----------------------------
# LOAD SESSION
# ----------------------------
@app.route("/load_session/<sid>")
def load_session(sid):

    if not session.get("user"):
        return jsonify({"error": "unauthorized"}), 401

    chats = ChatHistory.query.filter_by(
        session_id=sid
    ).order_by(ChatHistory.timestamp.asc()).all()

    return jsonify([
        {"role": c.role, "message": c.message}
        for c in chats
    ])

# ----------------------------
# HEALTH
# ----------------------------
@app.route("/health")
def health():
    return jsonify({
        "status": "ok",
        "users": len(USERS),
        "sessions": len(SESSION_INDEX),
        "history_rows": ChatHistory.query.count()
    })

# ----------------------------
# INIT DB
# ----------------------------
if __name__ == "__main__":
    with app.app_context():
        db.create_all()

    app.run(host="0.0.0.0", port=10000)
