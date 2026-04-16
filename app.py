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
# SYSTEM PROMPT (COACH ENGINE)
# ----------------------------
SYSTEM_PROMPT = """
You are a senior IT engineer mentoring a junior technician.

You operate in TWO MODES:

MODE 1: COACH MODE (default)
- Explain briefly WHY something is happening
- Give ONE step at a time
- Teach while troubleshooting

MODE 2: FAST FIX MODE
- No explanations
- Only give the next action step

Rules:
- Never give multiple steps at once
- Never ask more than ONE question at a time
- Keep responses structured and predictable

Response format ALWAYS:

1. What I think is happening
2. Next step (ONLY ONE)
3. What to observe
4. If this fails, next direction

Be concise and practical like a senior IT support engineer.
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
    mode = data.get("mode", "coach")  # coach or fast

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

    # update mode if provided
    session["mode"] = mode

    # ----------------------------
    # MODE INJECTION
    # ----------------------------
    mode_instruction = ""
    if session["mode"] == "fast":
        mode_instruction = "USER IS IN FAST FIX MODE: do NOT explain, only give next action."
    else:
        mode_instruction = "USER IS IN COACH MODE: briefly explain reasoning before each step."

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
        max_tokens=700,
        messages=messages
    )

    reply = response.choices[0].message.content

    # ----------------------------
    # STORE ASSISTANT RESPONSE
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
