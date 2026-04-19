from flask import Flask, render_template, request, jsonify, session
from openai import OpenAI
import os
import uuid

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-secret")

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

MODEL = "gpt-4.1-mini"

CHAT_MEMORY = {}
CASE_MEMORY = {}
MAX_HISTORY = 12

DIAG_PROMPT = """
You are an IT troubleshooting assistant.
Ask ONE question at a time. Do not repeat questions.
"""

FIX_PROMPT = """
You are in FIX MODE.

DO NOT ask questions.
ONLY provide solutions.

Each solution must start with:
Fix:
"""

def get_sid():
    if "sid" not in session:
        session["sid"] = str(uuid.uuid4())
    return session["sid"]

def ask_ai(messages):
    res = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        temperature=0.3
    )
    return res.choices[0].message.content

def update_case_memory(sid, text):
    if sid not in CASE_MEMORY:
        CASE_MEMORY[sid] = {"facts": {}}

    facts = CASE_MEMORY[sid]["facts"]
    t = text.lower()

    if "usb" in t:
        facts["connection"] = "USB"

    if "wifi" in t:
        facts["connection"] = "WiFi"

    if "windows 11" in t:
        facts["os"] = "Windows 11"

    if "ready" in t:
        facts["printer"] = "Ready"

    if "recognized" in t or "shows up" in t:
        facts["recognized"] = "Yes"

    if "doesn't print" in t or "not printing" in t:
        facts["issue"] = "Print failure"

    CASE_MEMORY[sid]["facts"] = facts

def should_use_fix_mode(facts):
    score = len(facts)
    return score >= 4

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/dashboard")
def dashboard():
    return render_template("dashboard.html")

@app.route("/chat", methods=["POST"])
def chat():
    sid = get_sid()
    user_input = request.json.get("message", "")

    update_case_memory(sid, user_input)
    facts = CASE_MEMORY[sid]["facts"]

    if sid not in CHAT_MEMORY:
        CHAT_MEMORY[sid] = []

    history = CHAT_MEMORY[sid]

    fix_mode = should_use_fix_mode(facts)
    system_prompt = FIX_PROMPT if fix_mode else DIAG_PROMPT

    messages = [{"role": "system", "content": system_prompt}]
    messages.append({"role": "system", "content": f"KNOWN FACTS: {facts}"})

    for m in history[-MAX_HISTORY:]:
        messages.append(m)

    messages.append({"role": "user", "content": user_input})

    reply = ask_ai(messages)

    history.append({"role": "user", "content": user_input})
    history.append({"role": "assistant", "content": reply})

    CHAT_MEMORY[sid] = history[-MAX_HISTORY:]

    return jsonify({
        "response": reply,
        "facts": facts,
        "fix_mode": fix_mode
    })

@app.route("/reset", methods=["POST"])
def reset():
    sid = get_sid()
    CHAT_MEMORY[sid] = []
    CASE_MEMORY[sid] = {}
    return jsonify({"status": "reset"})

if __name__ == "__main__":
    app.run(debug=True)
