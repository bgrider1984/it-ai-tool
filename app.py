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
# SYSTEM PROMPT (CORE COACH BEHAVIOR)
# ----------------------------
SYSTEM_PROMPT = """
You are a senior IT engineer coaching a junior technician.

Your job:
- Help troubleshoot IT issues step-by-step
- Teach while troubleshooting
- NEVER ask multiple questions at once
- ALWAYS give only ONE next action

Response format:

1. What I think is happening
2. One next step to try
3. What to look for
4. If it fails, next direction

Rules:
- Be concise
- Be practical
- Do NOT use forms, dropdowns, or multiple choice
- Do NOT overwhelm the user
- Think like a senior tech guiding a junior in real time
"""

# ----------------------------
# HOME
# ----------------------------
@app.route("/")
def home():
    return render_template("index.html")

# ----------------------------
# MAIN CHAT ENDPOINT
# ----------------------------
@app.route("/ask", methods=["POST"])
def ask():
    data = request.json
    user_input = data.get("message", "").strip()
    session_id = data.get("session_id")

    # ----------------------------
    # INIT SESSION
    # ----------------------------
    if not session_id or session_id not in sessions:
        session_id = str(uuid.uuid4())
        sessions[session_id] = {
            "messages": []
        }

    session = sessions[session_id]

    # ----------------------------
    # STORE USER MESSAGE
    # ----------------------------
    session["messages"].append({"role": "user", "content": user_input})

    # ----------------------------
    # BUILD CONTEXT
    # ----------------------------
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
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
        "response": reply
    })


# ----------------------------
# RUN APP
# ----------------------------
if __name__ == "__main__":
    app.run(debug=True)
