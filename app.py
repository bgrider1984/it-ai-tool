import os
import sys
import uuid
from flask import Flask, request, jsonify, render_template

# ----------------------------
# SAFE IMPORT WRAPPERS
# ----------------------------
def safe_import(module_name):
    try:
        return __import__(module_name)
    except Exception as e:
        print(f"[WARN] Missing optional dependency: {module_name} -> {e}")
        return None

stripe = safe_import("stripe")
bcrypt = safe_import("bcrypt")

from flask_sqlalchemy import SQLAlchemy
from openai import OpenAI

# ----------------------------
# APP INIT
# ----------------------------
app = Flask(__name__)

# ----------------------------
# ENV VALIDATION (NO CRASH)
# ----------------------------
REQUIRED_ENV_VARS = [
    "OPENAI_API_KEY",
    "DATABASE_URL"
]

missing = [v for v in REQUIRED_ENV_VARS if not os.getenv(v)]

if missing:
    print(f"[FATAL CONFIG ERROR] Missing: {missing}")
    # DO NOT CRASH HARD — allow Render to show error page
    app.config["CONFIG_ERROR"] = True
else:
    app.config["CONFIG_ERROR"] = False

# ----------------------------
# DATABASE
# ----------------------------
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL", "sqlite:///fallback.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)

# ----------------------------
# OPENAI SAFE INIT
# ----------------------------
client = None
if os.getenv("OPENAI_API_KEY"):
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ----------------------------
# MODELS (SAFE)
# ----------------------------
class Usage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    session = db.Column(db.String(120))
    issue = db.Column(db.Text)

# ----------------------------
# ERROR HANDLER (NO STACK TRACES TO USERS)
# ----------------------------
@app.errorhandler(Exception)
def handle_error(e):
    return jsonify({
        "error": "Internal server error",
        "message": str(e) if app.debug else "Something went wrong"
    }), 500

# ----------------------------
# HEALTH CHECK (RENDER USES THIS)
# ----------------------------
@app.route("/health")
def health():
    return jsonify({
        "status": "ok",
        "config_ok": not app.config["CONFIG_ERROR"],
        "stripe_loaded": stripe is not None,
        "bcrypt_loaded": bcrypt is not None,
        "openai_loaded": client is not None
    })

# ----------------------------
# HOME
# ----------------------------
@app.route("/")
def home():
    if app.config["CONFIG_ERROR"]:
        return """
        <h2>⚠ Configuration Error</h2>
        <p>Missing environment variables. Check server logs.</p>
        """, 500

    return render_template("index.html")

# ----------------------------
# AI ENGINE (SAFE FALLBACK)
# ----------------------------
def generate_response(message):

    if client is None:
        return "AI service not configured. Missing OPENAI_API_KEY."

    try:
        res = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[{
                "role": "user",
                "content": f"You are an IT help desk copilot. Be concise.\n\nIssue: {message}"
            }],
            temperature=0.2,
            max_tokens=400
        )

        return res.choices[0].message.content

    except Exception as e:
        return f"AI error fallback response: {str(e)}"

# ----------------------------
# MAIN ENDPOINT
# ----------------------------
@app.route("/ask", methods=["POST"])
def ask():

    data = request.json or {}
    message = data.get("message", "")
    session_id = data.get("session_id", str(uuid.uuid4()))

    if not message:
        return jsonify({"error": "No message provided"}), 400

    response = generate_response(message)

    db.session.add(Usage(session=session_id, issue=message))
    db.session.commit()

    return jsonify({
        "session_id": session_id,
        "response": response
    })

# ----------------------------
# SAFE STARTUP
# ----------------------------
if __name__ == "__main__":
    try:
        with app.app_context():
            db.create_all()

        print("✅ Server starting safely...")
        app.run(host="0.0.0.0", port=10000)

    except Exception as e:
        print(f"[FATAL STARTUP ERROR] {e}")
        sys.exit(1)
