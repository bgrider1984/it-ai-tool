from flask import Flask, render_template, request, jsonify, session
from openai import OpenAI
import os
import uuid
import time

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-secret-key-change-me")

# ----------------------------
# OpenAI Client
# ----------------------------
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

MODEL = "gpt-4.1-mini"  # stable + fast + cheap fallback model

# ----------------------------
# System Prompt (Helpdesk Brain)
# ----------------------------
SYSTEM_PROMPT = """
You are Adaptive Reasoning Helpdesk v15.

Your job:
- Diagnose technical issues step-by-step
- Ask ONE question at a time when needed
- Never repeat the same troubleshooting step twice
- If user already tried something, acknowledge it and move forward
- Escalate logically if issue persists
- Keep responses short, actionable, and structured

Rules:
1. Do NOT loop or repeat suggestions
2. If uncertain, narrow down with a diagnostic question
3. Prefer step-by-step elimination
4. If hardware/software ambiguity exists, separate both paths
5. If stuck after 3 attempts, provide a fallback diagnostic checklist
"""

# ----------------------------
# Simple Session Memory
# ----------------------------
def get_session_id():
    if "sid" not in session:
        session["sid"] = str(uuid.uuid4())
    return session["sid"]

# In-memory conversation store (swap for DB later if needed)
CHAT_MEMORY = {}

MAX_HISTORY = 12

# ----------------------------
# Core AI Call
# ----------------------------
def ask_ai(messages):
    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            temperature=0.4,
        )
        return response.choices[0].message.content

    except Exception as e:
        return f"⚠️ AI error occurred: {str(e)}"


# ----------------------------
# Route: Home
# ----------------------------
@app.route("/")
def index():
    return render_template("index.html")


# ----------------------------
# Route: Chat API
# ----------------------------
@app.route("/chat", methods=["POST"])
def chat():
    sid = get_session_id()

    user_input = request.json.get("message", "").strip()
    if not user_input:
        return jsonify({"response": "Please enter a message."})

    # init memory
    if sid not in CHAT_MEMORY:
        CHAT_MEMORY[sid] = []

    history = CHAT_MEMORY[sid]

    # Build messages
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    # Add memory (trimmed)
    for msg in history[-MAX_HISTORY:]:
        messages.append(msg)

    # Add new user message
    messages.append({"role": "user", "content": user_input})

    # Call AI
    start = time.time()
    reply = ask_ai(messages)
    duration = round(time.time() - start, 2)

    # Save memory
    history.append({"role": "user", "content": user_input})
    history.append({"role": "assistant", "content": reply})

    CHAT_MEMORY[sid] = history[-MAX_HISTORY:]

    return jsonify({
        "response": reply,
        "debug": {
            "response_time_sec": duration
        }
    })


# ----------------------------
# Route: Reset Session
# ----------------------------
@app.route("/reset", methods=["POST"])
def reset():
    sid = get_session_id()
    CHAT_MEMORY[sid] = []
    return jsonify({"status": "reset complete"})


# ----------------------------
# Run App
# ----------------------------
if __name__ == "__main__":
    app.run(debug=True)
