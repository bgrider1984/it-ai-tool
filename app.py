from flask import Flask, render_template, request, jsonify, session
from openai import OpenAI
import os
import uuid

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-secret")

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

MODEL = "gpt-4.1-mini"

# ----------------------------
# MEMORY
# ----------------------------
CHAT_MEMORY = {}
CASE_MEMORY = {}

MAX_HISTORY = 12


# ----------------------------
# SYSTEM PROMPTS
# ----------------------------
DIAG_PROMPT = """
You are an IT troubleshooting assistant.

Rules:
- Ask ONE question at a time
- Never repeat a question
- Stop asking once enough info is known
"""

FIX_PROMPT = """
You are an IT repair specialist in FIX MODE.

CRITICAL:
- DO NOT ask questions
- DO NOT gather more info
- ONLY provide solutions

Provide:
- Short explanation
- Multiple actionable fixes

Every fix MUST start with:
Fix:

Example:
Fix: Restart print spooler
Fix: Reinstall printer driver
Fix: Try different USB port
"""


# ----------------------------
# SESSION
# ----------------------------
def get_sid():
    if "sid" not in session:
        session["sid"] = str(uuid.uuid4())
    return session["sid"]


# ----------------------------
# AI CALL
# ----------------------------
def ask_ai(messages):
    try:
        res = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            temperature=0.3
        )
        return res.choices[0].message.content
    except Exception as e:
        return f"AI ERROR: {str(e)}"


# ----------------------------
# UPDATE CASE MEMORY
# ----------------------------
def update_case_memory(sid, text):
    if sid not in CASE_MEMORY:
        CASE_MEMORY[sid] = {"facts": {}}

    facts = CASE_MEMORY[sid]["facts"]
    t = text.lower()

    if "usb" in t:
        facts["connection"] = "usb"

    if "wifi" in t or "network" in t:
        facts["connection"] = "wifi"

    if "windows 11" in t:
        facts["os"] = "windows 11"

    if "windows 10" in t:
        facts["os"] = "windows 10"

    if "ready" in t:
        facts["printer_state"] = "ready"

    if "recognized" in t or "shows up" in t:
        facts["recognized"] = True

    if "doesn't print" in t or "not printing" in t:
        facts["printing_failure"] = True

    CASE_MEMORY[sid]["facts"] = facts


# ----------------------------
# DETERMINE MODE (NEW CORE LOGIC)
# ----------------------------
def should_use_fix_mode(facts):
    score = 0

    if "connection" in facts:
        score += 1
    if "os" in facts:
        score += 1
    if "printer_state" in facts:
        score += 1
    if "recognized" in facts:
        score += 1
    if "printing_failure" in facts:
        score += 2  # heavier weight

    return score >= 4  # threshold to switch to FIX MODE


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
        return jsonify({"response": "Empty input."})

    # Update memory
    update_case_memory(sid, user_input)
    facts = CASE_MEMORY.get(sid, {}).get("facts", {})

    # Init chat history
    if sid not in CHAT_MEMORY:
        CHAT_MEMORY[sid] = []

    history = CHAT_MEMORY[sid]

    # ----------------------------
    # MODE SWITCH
    # ----------------------------
    use_fix_mode = should_use_fix_mode(facts)

    if use_fix_mode:
        system_prompt = FIX_PROMPT
    else:
        system_prompt = DIAG_PROMPT

    # ----------------------------
    # BUILD MESSAGES
    # ----------------------------
    messages = [{"role": "system", "content": system_prompt}]

    messages.append({
        "role": "system",
        "content": f"""
KNOWN FACTS:
{facts}

If in FIX MODE, do not ask questions.
"""
    })

    for m in history[-MAX_HISTORY:]:
        messages.append(m)

    messages.append({"role": "user", "content": user_input})

    reply = ask_ai(messages)

    # Save history
    history.append({"role": "user", "content": user_input})
    history.append({"role": "assistant", "content": reply})

    CHAT_MEMORY[sid] = history[-MAX_HISTORY:]

    return jsonify({"response": reply})


@app.route("/reset", methods=["POST"])
def reset():
    sid = get_sid()
    CHAT_MEMORY[sid] = []
    CASE_MEMORY[sid] = {}
    return jsonify({"status": "reset complete"})


# ----------------------------
# RUN
# ----------------------------
if __name__ == "__main__":
    app.run(debug=True)
