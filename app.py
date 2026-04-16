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

app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL", "sqlite:///local.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

# ----------------------------
# OPENAI SETUP
# ----------------------------
client = None
if os.getenv("OPENAI_API_KEY"):
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ----------------------------
# MODELS
# ----------------------------
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

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

class Feedback(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer)
    message = db.Column(db.Text)
    response = db.Column(db.Text)
    helpful = db.Column(db.Boolean)

# ----------------------------
# HELPERS
# ----------------------------
def current_user():
    if "user_id" not in session:
        return None
    return User.query.get(session["user_id"])

def is_admin():
    user = current_user()
    return user and user.is_admin

# ----------------------------
# AI ENGINE
# ----------------------------
def ask_ai(message):
    if not client:
        return "AI not configured."

    res = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[
            {"role": "system", "content": "You are a fast Tier 2 IT help desk copilot. Be direct and structured."},
            {"role": "user", "content": message}
        ],
        temperature=0.2,
        max_tokens=400
    )

    return res.choices[0].message.content

# ----------------------------
# ROUTES
# ----------------------------

@app.route("/")
def home():
    if session.get("user_id"):
        return redirect("/dashboard")
    return render_template("index.html")

# ----------------------------
# AUTH
# ----------------------------
@app.route("/signup", methods=["POST"])
def signup():

    data = request.json or {}

    email = data.get("email","").strip()
    password = data.get("password","").strip()
    invite_code = data.get("invite_code","").strip()

    if not email or not password:
        return jsonify({"error":"Missing fields"}), 400

    invite = Invite.query.filter_by(code=invite_code, used=False).first()
    if not invite:
        return jsonify({"error":"Invalid invite code"}), 403

    if User.query.filter_by(email=email).first():
        return jsonify({"error":"User already exists"}), 400

    user = User(email=email, password=password)

    invite.used = True

    db.session.add(user)
    db.session.commit()

    return jsonify({"status":"created"})


@app.route("/login", methods=["POST"])
def login():

    data = request.json or {}

    email = data.get("email","").strip()
    password = data.get("password","").strip()

    user = User.query.filter_by(email=email, password=password).first()

    if not user:
        return jsonify({"error":"Invalid login"}), 401

    session["user_id"] = user.id

    return jsonify({"status":"ok"})


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

# ----------------------------
# DASHBOARD
# ----------------------------
@app.route("/dashboard")
def dashboard():
    if not session.get("user_id"):
        return redirect("/")
    return render_template("dashboard.html")

# ----------------------------
# CHAT ENGINE
# ----------------------------
@app.route("/ask", methods=["POST"])
def ask():

    user = current_user()
    if not user:
        return jsonify({"error":"unauthorized"}), 401

    data = request.json
    message = data.get("message")

    response = ask_ai(message)

    db.session.add(ChatLog(
        user_id=user.id,
        message=message,
        response=response
    ))

    db.session.commit()

    return jsonify({"response": response})

# ----------------------------
# FEEDBACK SYSTEM
# ----------------------------
@app.route("/feedback", methods=["POST"])
def feedback():

    user = current_user()
    if not user:
        return jsonify({"error":"unauthorized"}), 401

    data = request.json

    fb = Feedback(
        user_id=user.id,
        message=data.get("message"),
        response=data.get("response"),
        helpful=data.get("helpful")
    )

    db.session.add(fb)
    db.session.commit()

    return jsonify({"status":"ok"})

# ----------------------------
# ADMIN: GENERATE INVITE
# ----------------------------
@app.route("/admin/invite", methods=["POST"])
def generate_invite():

    if not is_admin():
        return jsonify({"error":"forbidden"}), 403

    code = str(uuid.uuid4())[:8]

    invite = Invite(code=code)
    db.session.add(invite)
    db.session.commit()

    return jsonify({"invite": code})

# ----------------------------
# ANALYTICS v2 (ADMIN)
# ----------------------------
@app.route("/analytics")
def analytics():

    if not is_admin():
        return "Unauthorized", 403

    users = User.query.count()
    messages = ChatLog.query.count()
    feedback_total = Feedback.query.count()
    helpful = Feedback.query.filter_by(helpful=True).count()
    not_helpful = Feedback.query.filter_by(helpful=False).count()

    recent_issues = ChatLog.query.order_by(ChatLog.created_at.desc()).limit(20).all()

    issue_texts = [i.message for i in recent_issues]

    return render_template(
        "analytics.html",
        total_users=users,
        total_messages=messages,
        total_feedback=feedback_total,
        helpful=helpful,
        not_helpful=not_helpful,
        issues=issue_texts
    )

# ----------------------------
# INIT DB
# ----------------------------
if __name__ == "__main__":
    with app.app_context():
        db.create_all()

        # ensure admin exists
        if not User.query.filter_by(is_admin=True).first():
            admin = User(
                email="admin@local",
                password="admin",
                is_admin=True
            )
            db.session.add(admin)
            db.session.commit()

    app.run(host="0.0.0.0", port=10000)
