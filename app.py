from flask import Flask, render_template, request, jsonify, session
from openai import OpenAI
import os
import uuid

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-secret")

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

MODEL = "gpt-4.1-mini"

# ----------------------------
# MEMORY STORAGE
# ----------------------------
CHAT_MEMORY = {}
CASE_MEMORY = {}  # NEW: structured facts per session

MAX_HISTORY = 12

# ----------------------------
# SYSTEM PROMPT (UPDATED)
# ----------------------------
SYSTEM_PROMPT = """
You are an IT troubleshooting assistant.

CRITICAL RULES:
- NEVER ask the same question twice if the user already answered it.
- Before asking a question, check if the information is already known.
- Maintain an internal "case profile" of known facts:
  - connection type (USB/WiFi)
  - OS version
  - error state
  - device status

Behavior:
- If a fact is already known, do NOT re-ask it.
- Instead, proceed to next unknown diagnostic step.
- Be step-by-step, but NOT repetitive.
- Prefer direct fixes when enough info is known.

If enough information exists:
- STOP questioning
- MOVE to solutions immediately
"""


# ----------------------------
# SESSION ID
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
# UPDATE CASE MEMORY (NEW CORE FEATURE)
# ----------------------------
def update_case_memory(sid, user_text):
    if sid not in CASE_MEMORY:
        CASE_MEMORY[sid] = {
            "facts": {}
        }

    facts = CASE_MEMORY[sid]["facts"]

    text = user_text.lower()

    # Detect USB connection
    if "usb" in text:
        facts["connection"] = "usb"

    # Detect WiFi/network
    if "wifi" in text or "network" in text:
        facts["connection"] = "wifi"

    # Detect OS
    if "windows 11" in text:
        facts["os"] = "windows 11"

    if "windows 10" in text:
        facts["os"] = "windows 10"

    # Printer ready state
    if "ready" in text:
        facts["printer_state"] = "ready"

    CASE_MEMORY[sid]["facts"] = facts


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

    # ----------------------------
    # Update structured memory
    # ----------------------------
    update_case_memory(sid, user_input)

    facts = CASE_MEMORY.get(sid, {}).get("facts", {})

    # ----------------------------
    # INIT MEMORY
    # ----------------------------
    if sid not in CHAT_MEMORY:
        CHAT_MEMORY[sid] = []

    history = CHAT_MEMORY[sid]

    # ----------------------------
    # BUILD MESSAGE CONTEXT
    # ----------------------------
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    # Inject structured case memory (VERY IMPORTANT FIX)
    messages.append({
        "role": "system",
        "content": f"""
KNOWN CASE FACTS:
{facts}

Do NOT ask about these again.
"""
    })

    # Add chat history
    for m in history[-MAX_HISTORY:]:
        messages.append(m)

    messages.append({"role": "user", "content": user_input})

    reply = ask_ai(messages)

    # Save memory
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
