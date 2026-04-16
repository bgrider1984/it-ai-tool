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
# USERS / INVITES
# ----------------------------
USERS = {"admin@local": {"password": "admin", "is_admin": True}}
INVITES = set()

# ----------------------------
# CHAT HISTORY MODEL
# ----------------------------
class ChatHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user = db.Column(db.String(120))
    role = db.Column(db.String(20))  # user / assistant
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
        sessions[sid] = {"history": [], "issue": None}
    return sessions[sid]

# ----------------------------
# AUTH
# ----------------------------
def current_user():
    return session.get("user")

# ----------------------------
# HOME
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
# ASK + SAVE HISTORY
# ----------------------------
@app.route("/ask", methods=["POST"])
def ask():

    if not session.get("user"):
        return jsonify({"error": "unauthorized"}), 401

    data = request.json
    msg = data.get("message")

    sid = session.get("sid") or str(uuid.uuid4())
    session["sid"] = sid

    state = get_session()
    state["history"].append(msg)

    # simple intelligence
    if "vpn" in msg.lower():
        reply = "Check VPN connection and reconnect."
    elif "outlook" in msg.lower():
        reply = "Restart Outlook and test Safe Mode."
    elif "crash" in msg.lower():
        reply = "Check Task Manager for CPU/RAM spikes."
    else:
        reply = "Restart device and retest."

    # SAVE USER MESSAGE
    db.session.add(ChatHistory(
        user=session["user"],
        role="user",
        message=msg,
        session_id=sid
    ))

    # SAVE AI RESPONSE
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
# GET CHAT HISTORY (NEW)
# ----------------------------
@app.route("/history")
def history():

    if not session.get("user"):
        return jsonify({"error": "unauthorized"}), 401

    chats = ChatHistory.query.filter_by(
        user=session["user"]
    ).order_by(ChatHistory.timestamp.asc()).all()

    return jsonify([
        {
            "role": c.role,
            "message": c.message,
            "time": str(c.timestamp)
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
        "history_rows": ChatHistory.query.count()
    })

# ----------------------------
# INIT DB
# ----------------------------
if __name__ == "__main__":
    with app.app_context():
        db.create_all()

    app.run(host="0.0.0.0", port=10000)
