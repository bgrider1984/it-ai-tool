import os
import uuid
from flask import Flask, render_template, request, jsonify
from openai import OpenAI

app = Flask(__name__)

# ----------------------------
# OPENAI SETUP
# ----------------------------
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise RuntimeError("Missing OPENAI_API_KEY")

client = OpenAI(api_key=api_key)

# ----------------------------
# SESSION STORAGE
# ----------------------------
sessions = {}

# ----------------------------
# DETECT MISTAKE SIGNALS
# ----------------------------
def detect_confusion(messages):
    """
    Simple heuristic to detect if user is struggling.
    """
    recent = messages[-4:] if len(messages) >= 4 else messages

    text_blob = " ".join([m["content"].lower() for m in recent if m["role"] == "user"])

    signals = 0

    confusion_phrases = [
        "not sure",
        "i don't know",
        "no idea",
        "doesn't work",
        "still not",
        "same issue",
        "nothing happens",
        "didn't work"
    ]

    for phrase in confusion_phrases:
        if phrase in text_blob:
            signals += 1

    return signals >= 2  # threshold for “user is struggling”

# ----------------------------
# SYSTEM PROMPT (ENHANCED COACH)
# ----------------------------
SYSTEM_PROMPT = """
You are a senior IT engineer mentoring a junior technician.

You operate in three modes:

COACH MODE:
- Teach while troubleshooting
- One step at a time

FAST MODE:
- No explanation
- Only next step

TRAINING MODE:
- One step
- Then ask what happened

IMPORTANT BEHAVIOR RULES:
- NEVER give multiple steps at once
- ALWAYS wait for user response before advancing
- Be concise and structured

Response format:

1. What I think is happening
2. Next step (ONLY ONE)
3. What to observe
4. If it fails, next direction
"""

# ----------------------------
# HOME
# ----------------------------
@app.route("/")
def home():
    return render_template("index.html")

# ----------------------------
# MAIN ENDPOINT
# ----------------------------
@app.route("/ask", methods=["POST"])
def ask():
    data = request.json
    user_input = data.get("message", "").strip()
    session_id = data.get("session_id")
    mode = data.get("mode", "coach")

    # ----------------------------
    # INIT SESSION
    # ----------------------------
    if not session_id or session_id not in sessions:
        session_id = str(uuid.uuid4())
        sessions[session_id] = {
            "messages": [],
            "mode": "coach"
        }

    session = sessions[session_id]
    session["mode"] = mode

    # ----------------------------
    # STORE USER MESSAGE
    # ----------------------------
    session["messages"].append({"role": "user", "content": user_input})

    # ----------------------------
    # MISTAKE DETECTION
    # ----------------------------
    struggling = detect_confusion(session["messages"])

    # ----------------------------
    # MODE INSTRUCTIONS
    # ----------------------------
    if mode == "fast":
        mode_instruction = "FAST MODE: no explanation, only next action."
    elif mode == "training":
        mode_instruction = "TRAINING MODE: teach and ask what happened after each step."
    else:
        mode_instruction = "COACH MODE: explain briefly and guide step-by-step."

    # ----------------------------
    # ADD MISTAKE DETECTION BEHAVIOR
    # ----------------------------
    if struggling:
        mode_instruction += """
USER APPEARS CONFUSED:
- Slow down
- Re-explain the last step more simply
- Do NOT advance steps until user confirms understanding
- Ask a single clarifying question if needed
"""

    # ----------------------------
    # BUILD CONTEXT
    # ----------------------------
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT + "\n" + mode_instruction}
    ]
    messages.extend(session["messages"])

    # ----------------------------
    # AI CALL
    # ----------------------------
    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        max_tokens=800,
        messages=messages
    )

    reply = response.choices[0].message.content

    # ----------------------------
    # STORE RESPONSE
    # ----------------------------
    session["messages"].append({"role": "assistant", "content": reply})

    return jsonify({
        "session_id": session_id,
        "response": reply,
        "confusion_detected": struggling
    })


# ----------------------------
# RUN APP
# ----------------------------
if __name__ == "__main__":
    app.run(debug=True)
