import os
import uuid
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from openai import OpenAI

app = Flask(__name__)

# ----------------------------
# SECURITY KEY (REQUIRED FOR LOGIN SESSIONS)
# ----------------------------
app.secret_key = os.getenv("SECRET_KEY", "dev-secret-change-me")

# ----------------------------
# DATABASE
# ----------------------------
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL", "sqlite:///local.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)

# ----------------------------
# OPENAI
# ----------------------------
client = None
if os.getenv("OPENAI_API_KEY"):
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ----------------------------
# MODELS
# ----------------------------
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True)
    password = db.Column(db.String(120))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class ChatLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer)
    message = db.Column(db.Text)
    response = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

# ----------------------------
# AI ENGINE
# ----------------------------
def ask_ai(message):
    if not client:
        return "AI not configured."

    res = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[
            {"role": "system", "content": "You are a fast Tier 2 IT Copilot. Give direct troubleshooting steps."},
            {"role": "user", "content": message}
        ],
        temperature=0.2,
        max_tokens=500
    )
    return res.choices[0].message.content

# ----------------------------
# AUTH ROUTES
# ----------------------------
@app.route("/", methods=["GET"])
def home():
    if "user_id" in session:
        return redirect("/dashboard")
    return render_template("index.html")

@app.route("/signup", methods=["POST"])
def signup():
    data = request.json

    user = User(
        email=data["email"],
        password=data["password"]  # (upgrade later to bcrypt)
    )

    db.session.add(user)
    db.session.commit()

    return jsonify({"status": "created"})

@app.route("/login", methods=["POST"])
def login():
    data = request.json

    user = User.query.filter_by(
        email=data["email"],
        password=data["password"]
    ).first()

    if not user:
        return jsonify({"error": "invalid login"}), 401

    session["user_id"] = user.id
    return jsonify({"status": "logged_in"})

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

# ----------------------------
# DASHBOARD UI
# ----------------------------
@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect("/")
    return render_template("dashboard.html")

# ----------------------------
# CHAT API
# ----------------------------
@app.route("/ask", methods=["POST"])
def ask():
    if "user_id" not in session:
        return jsonify({"error": "unauthorized"}), 401

    data = request.json
    message = data.get("message")

    response = ask_ai(message)

    db.session.add(ChatLog(
        user_id=session["user_id"],
        message=message,
        response=response
    ))
    db.session.commit()

    return jsonify({"response": response})

# ----------------------------
# INIT DB
# ----------------------------
if __name__ == "__main__":
    with app.app_context():
        db.create_all()

    app.run(host="0.0.0.0", port=10000)
