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
# USERS / INVITES (BETA SIMPLE)
# ----------------------------
USERS = {
    "admin@local": {"password": "admin", "is_admin": True}
}

INVITES = set()

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
# SESSION MEMORY (IN-MEMORY INDEX)
# ----------------------------
SESSION_INDEX = {}

sessions = {}

# ----------------------------
# HELPERS
# ----------------------------
def get_session_title(message):
    t = message.lower()
    if "vpn" in t:
        return "VPN Issue"
    if "outlook" in t:
        return "Outlook Issue"
    if "login" in t:
        return "Login Issue"
    if "crash" in t:
        return "System Crash"
    if "slow" in t:
        return "Performance Issue"
    return "General IT Issue"

def get_session():
    sid = session.get("sid")

    if not sid:
        sid = str(uuid.uuid4())
        session["sid"] = sid
        sessions[sid] = {"step": 0, "history": []}

    return sid

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
# LOGIN (BETA SIMPLE)
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
# ASK (COPILOT RESPONSE + HISTORY SAVE)
# ----------------------------
@app.route("/ask", methods=["POST"])
def ask():

    if not session.get("user"):
        return jsonify({"error": "unauthorized"}), 401

    data = request.json
    message = data.get("message", "")

    sid = get_session()

    # create session index entry if new
    if sid not in SESSION_INDEX:
        SESSION_INDEX[sid] = {
            "title": get_session_title(message),
            "created": str(datetime.utcnow())
        }

    # simple AI logic (beta)
    msg = message.lower()

    if "vpn" in msg:
        reply = "Check VPN connection → reconnect client."
    elif "outlook" in msg:
        reply = "Restart Outlook → try Safe Mode."
    elif "crash" in msg:
        reply = "Check Task Manager → CPU/RAM usage."
    elif "slow" in msg:
        reply = "Check disk usage and background processes."
    else:
        reply = "Restart device and re-test issue."

    # SAVE USER MESSAGE
    db.session.add(ChatHistory(
        user=session["user"],
        role="user",
        message=message,
        session_id=sid
    ))

    # SAVE ASSISTANT MESSAGE
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
# LIST SESSIONS (SIDEBAR)
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
# LOAD SESSION HISTORY
# ----------------------------
@app.route("/load_session/<sid>")
def load_session(sid):

    if not session.get("user"):
        return jsonify({"error": "unauthorized"}), 401

    chats = ChatHistory.query.filter_by(
        session_id=sid
    ).order_by(ChatHistory.timestamp.asc()).all()

    return jsonify([
        {
            "role": c.role,
            "message": c.message
        }
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
