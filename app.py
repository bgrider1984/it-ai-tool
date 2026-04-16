import os
import uuid
from datetime import datetime
from flask import Flask, request, jsonify, session, redirect, render_template
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)

app.secret_key = os.getenv("SECRET_KEY", "dev-secret")

app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_SECURE"] = True

app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv(
    "DATABASE_URL",
    "sqlite:///local.db"
)

app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

# ----------------------------
# USERS (BETA)
# ----------------------------
USERS = {"admin@local": {"password": "admin", "is_admin": True}}
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
# SAFE SESSION
# ----------------------------
def get_session_id():
    if "sid" not in session:
        session["sid"] = str(uuid.uuid4())
    return session["sid"]

# ----------------------------
# INTENT CLASSIFIER
# ----------------------------
def classify_intent(msg):
    t = msg.lower()

    vague = ["won't", "not working", "won’t", "doesn't", "broken", "issue"]
    specific = ["error", "crash", "blue screen", "vpn", "outlook"]

    if any(v in t for v in vague):
        return "clarify"

    if any(s in t for s in specific):
        return "direct"

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

@app.route("/login", methods=["POST"])
def login():
    data = request.json

    user = USERS.get(data.get("email"))

    if not user or user["password"] != data.get("password"):
        return jsonify({"error": "invalid login"}), 401

    session["user"] = data["email"]
    return jsonify({"status": "ok"})

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

# ----------------------------
# ASK (CRASH-PROOF VERSION)
# ----------------------------
@app.route("/ask", methods=["POST"])
def ask():

    try:
        if not session.get("user"):
            return jsonify({"error": "unauthorized"}), 401

        data = request.json or {}
        message = data.get("message", "")

        sid = get_session_id()

        # ensure session index exists
        if sid not in SESSION_INDEX:
            SESSION_INDEX[sid] = {
                "title": message[:30] if message else "New Session",
                "created": str(datetime.utcnow())
            }

        intent = classify_intent(message)

        if intent == "clarify":
            reply = (
                "I need a bit more detail:\n"
                "1. Is this affecting all apps or one?\n"
                "2. Did this start recently or after changes?\n"
                "3. Any error messages?"
            )
        else:
            m = message.lower()

            if "vpn" in m:
                reply = "Reconnect VPN → verify internet"
            elif "outlook" in m:
                reply = "Restart Outlook → Safe Mode test"
            elif "crash" in m:
                reply = "Check Task Manager → CPU/RAM usage"
            else:
                reply = "Restart device → re-test issue"

        # SAFE DB WRITE (prevents 500 crash)
        try:
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

        except Exception as db_error:
            print("DB ERROR:", db_error)
            db.session.rollback()

        return jsonify({
            "response": reply,
            "session_id": sid
        })

    except Exception as e:
        print("ASK ERROR:", e)
        return jsonify({"error": "internal server error"}), 500

# ----------------------------
# SESSIONS
# ----------------------------
@app.route("/sessions")
def sessions_list():
    if not session.get("user"):
        return jsonify({"error": "unauthorized"}), 401

    return jsonify([
        {
            "session_id": sid,
            "title": data["title"]
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
        "sessions": len(SESSION_INDEX)
    })

# ----------------------------
# INIT DB
# ----------------------------
if __name__ == "__main__":
    with app.app_context():
        db.create_all()

    app.run(host="0.0.0.0", port=10000)
