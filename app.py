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
# SYSTEM PROMPT (COACH + TRAINING ENGINE)
# ----------------------------
SYSTEM_PROMPT = """
You are a senior IT engineer acting as both:

1. Troubleshooting assistant
2. Junior IT trainer

You operate in three modes:

MODE 1: COACH MODE
- Explain briefly why
- Give ONE step
- Continue based on response

MODE 2: FAST FIX MODE
- No explanations
- Only next action

MODE 3: TRAINING MODE
- Give ONE step
- THEN ask what happened after the step
- Reinforce learning
- Confirm understanding before continuing

Rules:
- Always give ONLY ONE step at a time
- Never overwhelm the user
- Never give multiple steps in a list
- Keep responses structured

Response format:

1. What I think is happening
2. Next step (ONLY ONE)
3. What to observe
4. If it fails, next direction

In TRAINING MODE ONLY:
Add at the end:
"👉 What happened when you tried this?"
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
    # MODE INSTRUCTIONS
    # ----------------------------
    if mode == "fast":
        mode_instruction = "FAST FIX MODE: No explanations. Only next action."
    elif mode == "training":
        mode_instruction = "TRAINING MODE: Teach by doing. After each step, ask what happened."
    else:
        mode_instruction = "COACH MODE: Brief explanation plus next step."

    # ----------------------------
    # STORE USER MESSAGE
    # ----------------------------
    session["messages"].append({"role": "user", "content": user_input})

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
        "mode": session["mode"]
    })


# ----------------------------
# RUN APP
# ----------------------------
if __name__ == "__main__":
    app.run(debug=True)
