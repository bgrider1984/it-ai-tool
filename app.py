from flask import Flask, render_template, request, jsonify, session
from openai import OpenAI
import os
import uuid
import time

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-secret")

# ----------------------------
# OpenAI Client
# ----------------------------
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

MODEL = "gpt-4.1-mini"

# ----------------------------
# System Prompt (Helpdesk Brain)
# ----------------------------
SYSTEM_PROMPT = """
You are AI Troubleshooting Assistant v15.

Behavior rules:
- Diagnose issues step-by-step
- Never repeat the same troubleshooting step
- Ask one question at a time when needed
- Prefer actionable fixes
- If possible, include lines starting with "Fix:" for UI quick actions
"""

# ----------------------------
# Session Memory
# ----------------------------
CHAT_MEMORY = {}
MAX_HISTORY = 12


def get_sid():
    if "sid" not in session:
        session["sid"] = str(uuid.uuid4())
    return session["sid"]


def ask_ai(messages):
    try:
        res = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            temperature=0.4
        )
        return res.choices[0].message.content
    except Exception as e:
        return f"AI ERROR: {str(e)}"


# ----------------------------
# ROUTES
# ----------------------------

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/dashboard")
def dashboard():
    return render_template("dashboard.html")


@app.route("/chat", methods=["POST"])
def chat():
    sid = get_sid()
    user_input = request.json.get("message", "").strip()

    if not user_input:
        return jsonify({"response": "Empty input received."})

    if sid not in CHAT_MEMORY:
        CHAT_MEMORY[sid] = []

    history = CHAT_MEMORY[sid]

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    for m in history[-MAX_HISTORY:]:
        messages.append(m)

    messages.append({"role": "user", "content": user_input})

    reply = ask_ai(messages)

    history.append({"role": "user", "content": user_input})
    history.append({"role": "assistant", "content": reply})

    CHAT_MEMORY[sid] = history[-MAX_HISTORY:]

    return jsonify({"response": reply})


@app.route("/reset", methods=["POST"])
def reset():
    sid = get_sid()
    CHAT_MEMORY[sid] = []
    return jsonify({"status": "reset ok"})


# ----------------------------
# RUN APP
# ----------------------------
if __name__ == "__main__":
    app.run(debug=True)
