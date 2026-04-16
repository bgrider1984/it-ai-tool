import os
import uuid
import stripe
from flask import Flask, request, jsonify, session, redirect, render_template
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from openai import OpenAI

# ----------------------------
# APP INIT
# ----------------------------
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "dev-key-change-me")

# ----------------------------
# STRIPE INIT
# ----------------------------
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
STRIPE_PRICE_ID = os.getenv("STRIPE_PRICE_ID")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")

# ----------------------------
# DATABASE
# ----------------------------
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)

# ----------------------------
# OPENAI
# ----------------------------
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ----------------------------
# MODELS
# ----------------------------
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True)
    password = db.Column(db.String(120))
    plan = db.Column(db.String(20), default="free")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Usage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer)
    count = db.Column(db.Integer, default=0)

# ----------------------------
# LIMITS
# ----------------------------
FREE_LIMIT = 10

# ----------------------------
# AI ENGINE
# ----------------------------
def ask_ai(message):
    res = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[
            {"role": "system", "content": "You are a Tier 2 IT Copilot. Be fast and direct."},
            {"role": "user", "content": message}
        ],
        temperature=0.2
    )
    return res.choices[0].message.content

# ----------------------------
# AUTH
# ----------------------------
@app.route("/")
def home():
    return render_template("index.html")

@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect("/")
    return render_template("dashboard.html")

@app.route("/signup", methods=["POST"])
def signup():
    data = request.json

    user = User(
        email=data["email"],
        password=data["password"]
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
        return jsonify({"error": "invalid"}), 401

    session["user_id"] = user.id
    return jsonify({"status": "ok"})

# ----------------------------
# STRIPE CHECKOUT
# ----------------------------
@app.route("/create-checkout-session", methods=["POST"])
def create_checkout():

    if "user_id" not in session:
        return jsonify({"error": "unauthorized"}), 401

    user = User.query.get(session["user_id"])

    checkout = stripe.checkout.Session.create(
        payment_method_types=["card"],
        mode="subscription",
        customer_email=user.email,
        line_items=[{
            "price": STRIPE_PRICE_ID,
            "quantity": 1
        }],
        success_url="https://your-app.onrender.com/success",
        cancel_url="https://your-app.onrender.com/cancel"
    )

    return jsonify({"url": checkout.url})

@app.route("/success")
def success():
    return "Payment successful. You can close this tab."

@app.route("/cancel")
def cancel():
    return "Payment canceled."

# ----------------------------
# STRIPE WEBHOOK (CRITICAL)
# ----------------------------
@app.route("/stripe-webhook", methods=["POST"])
def stripe_webhook():

    payload = request.data
    sig_header = request.headers.get("Stripe-Signature")

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, STRIPE_WEBHOOK_SECRET
        )
    except:
        return "invalid", 400

    if event["type"] == "checkout.session.completed":
        session_data = event["data"]["object"]
        email = session_data["customer_email"]

        user = User.query.filter_by(email=email).first()
        if user:
            user.plan = "pro"
            db.session.commit()

    return "ok"

# ----------------------------
# CHAT (WITH PAYWALL)
# ----------------------------
@app.route("/ask", methods=["POST"])
def ask():

    user = User.query.get(session["user_id"])

    usage = Usage.query.filter_by(user_id=user.id).first()
    if not usage:
        usage = Usage(user_id=user.id, count=0)
        db.session.add(usage)
        db.session.commit()

    # PAYWALL
    if user.plan == "free" and usage.count >= FREE_LIMIT:
        return jsonify({
            "response": "Free limit reached. Upgrade to Pro to continue.",
            "upgrade": True
        })

    data = request.json
    message = data["message"]

    response = ask_ai(message)

    usage.count += 1
    db.session.commit()

    return jsonify({"response": response})

# ----------------------------
# INIT DB
# ----------------------------
if __name__ == "__main__":
    with app.app_context():
        db.create_all()

    app.run(host="0.0.0.0", port=10000)
