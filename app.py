import os
import uuid
import stripe
import bcrypt
from flask import Flask, request, jsonify, render_template
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

app = Flask(__name__)

# ----------------------------
# CONFIG
# ----------------------------
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
STRIPE_PRICE_ID = os.getenv("STRIPE_PRICE_ID")

# ----------------------------
# DATABASE MODELS
# ----------------------------
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.LargeBinary, nullable=False)
    plan = db.Column(db.String(20), default="free")
    stripe_customer_id = db.Column(db.String(120))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Usage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

class Session(db.Model):
    id = db.Column(db.String(120), primary_key=True)
    user_id = db.Column(db.Integer)
    history = db.Column(db.Text)

# ----------------------------
# HELPERS
# ----------------------------
def hash_password(password):
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt())

def check_password(password, hashed):
    return bcrypt.checkpw(password.encode(), hashed)

def get_user_by_token(token):
    return User.query.filter_by(id=token).first()

# ----------------------------
# AI ENGINE
# ----------------------------
def generate_response(message, history):

    prompt = f"""
You are a Tier 2 IT Help Desk Copilot.

Be concise and practical.

Format:
🔴 Fix first:
🟡 Next steps:
🔵 Escalation:

Issue:
{message}

History:
{history}
"""

    res = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
        max_tokens=500
    )

    return res.choices[0].message.content

# ----------------------------
# ROUTES
# ----------------------------
@app.route("/")
def home():
    return render_template("index.html")

# ----------------------------
# SIGNUP
# ----------------------------
@app.route("/signup", methods=["POST"])
def signup():

    data = request.json
    email = data["email"]
    password = hash_password(data["password"])

    if User.query.filter_by(email=email).first():
        return jsonify({"error": "User exists"}), 400

    user = User(email=email, password=password)
    db.session.add(user)
    db.session.commit()

    return jsonify({"message": "User created"})

# ----------------------------
# LOGIN
# ----------------------------
@app.route("/login", methods=["POST"])
def login():

    data = request.json
    user = User.query.filter_by(email=data["email"]).first()

    if not user or not check_password(data["password"], user.password):
        return jsonify({"error": "Invalid credentials"}), 401

    return jsonify({"user_id": user.id, "plan": user.plan})

# ----------------------------
# STRIPE CHECKOUT
# ----------------------------
@app.route("/create-checkout", methods=["POST"])
def create_checkout():

    data = request.json
    user = User.query.get(data["user_id"])

    session = stripe.checkout.Session.create(
        payment_method_types=["card"],
        mode="subscription",
        line_items=[{
            "price": STRIPE_PRICE_ID,
            "quantity": 1
        }],
        success_url="https://yourdomain.com/success",
        cancel_url="https://yourdomain.com/cancel",
        customer_email=user.email
    )

    return jsonify({"url": session.url})

# ----------------------------
# STRIPE WEBHOOK
# ----------------------------
@app.route("/stripe-webhook", methods=["POST"])
def stripe_webhook():

    payload = request.data
    event = stripe.Event.construct_from(
        request.json, stripe.api_key
    )

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        email = session["customer_email"]

        user = User.query.filter_by(email=email).first()
        if user:
            user.plan = "pro"
            db.session.commit()

    return jsonify({"status": "ok"})

# ----------------------------
# MAIN AI REQUEST
# ----------------------------
@app.route("/ask", methods=["POST"])
def ask():

    data = request.json

    user_id = data.get("user_id")
    message = data.get("message", "")
    session_id = data.get("session_id")

    user = User.query.get(user_id)

    if not user:
        return jsonify({"error": "Invalid user"}), 403

    # usage tracking
    usage = Usage(user_id=user.id)
    db.session.add(usage)
    db.session.commit()

    # simple free tier limit
    if user.plan == "free":
        count = Usage.query.filter_by(user_id=user.id).count()
        if count > 50:
            return jsonify({"error": "Upgrade to Pro"}), 403

    session = Session.query.get(session_id)

    if not session:
        session_id = str(uuid.uuid4())
        session = Session(id=session_id, user_id=user.id, history="")

    session.history += f"\n{message}"
    db.session.add(session)
    db.session.commit()

    response = generate_response(message, session.history)

    return jsonify({
        "session_id": session_id,
        "response": response,
        "plan": user.plan
    })


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)
