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

# ----------------------------
# SESSION STATE ENGINE
# ----------------------------
sessions = {}

def get_session_id():
    if "sid" not in session:
        sid = str(uuid.uuid4())
        session["sid"] = sid

        sessions[sid] = {
            "step": 0,
            "history": [],
            "last_intent": None
        }

    return session["sid"]

# ----------------------------
# CHAT MODEL (optional persistence)
# ----------------------------
class ChatHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user = db.Column(db.String(120))
    role = db.Column(db.String(20))
    message = db.Column(db.Text)
    session_id = db.Column(db.String(80))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

# ----------------------------
# INTENT ENGINE
# ----------------------------
def classify(msg):
    t = msg.lower()

    vague = ["won't", "not working", "broken", "issue", "problem"]
    specific = ["error", "crash", "vpn", "outlook", "blue screen"]

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
# CORE COPILOT ENGINE (NO LOOPS)
# ----------------------------
@app.route("/ask", methods=["POST"])
def ask():

    if not session.get("user"):
        return jsonify({"error": "unauthorized"}), 401

    data = request.json or {}
    msg = data.get("message", "")

    sid = get_session_id()
    state = sessions[sid]

    state["history"].append(msg.lower())

    intent = classify(msg)

    # ----------------------------
    # STEP 0: ALWAYS CLARIFY FIRST
    # ----------------------------
    if state["step"] == 0:
        reply = (
            "Before I fix this, I need clarity:\n\n"
            "• Is this happening to ALL apps or just one?\n"
            "• Did this start after a restart or update?\n"
            "• Any error messages?"
        )
        state["step"] = 1

    # ----------------------------
    # STEP 1: INTERPRET RESPONSE
    # ----------------------------
    elif state["step"] == 1:

        t = msg.lower()

        if "all" in t:
            reply = "System-wide issue detected → Check Task Manager (CPU/RAM usage)."
        elif "one" in t:
            reply = "App-specific issue → Try reinstalling or Safe Mode."
        elif "update" in t or "restart" in t:
            reply = "Recent change detected → Consider system restore."
        else:
            reply = "Need more detail: is it ALL apps or just ONE?"

        state["step"] = 2

    # ----------------------------
    # STEP 2: FIX PHASE
    # ----------------------------
    else:
        reply = (
            "Try these steps:\n\n"
            "1. Restart your computer\n"
            "2. Check startup apps\n"
            "3. Run antivirus scan\n"
            "4. Check disk health"
        )

    return jsonify({
        "response": reply,
        "session_id": sid
    })

# ----------------------------
# HEALTH
# ----------------------------
@app.route("/health")
def health():
    return jsonify({
        "status": "ok",
        "users": len(USERS),
        "sessions": len(sessions)
    })

# ----------------------------
# INIT DB
# ----------------------------
if __name__ == "__main__":
    with app.app_context():
        db.create_all()

    app.run(host="0.0.0.0", port=10000)
