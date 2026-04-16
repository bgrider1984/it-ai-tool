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
# SESSION STORAGE (simple memory)
# ----------------------------
sessions = {}

# ----------------------------
# SYSTEM PROMPT (REAL IT COPILOT MODE)
# ----------------------------
SYSTEM_PROMPT = """
You are a senior IT support engineer (Tier 2 level).

Your job:
- Quickly diagnose IT issues
- Ask only necessary clarifying questions
- Provide actionable steps
- Avoid over-explaining
- Keep responses short and practical

Format:
1. Likely cause
2. Immediate next step
3. Optional follow-up question (only if needed)

Do NOT behave like a training system.
Do NOT give multiple long teaching steps unless required.
"""

# ----------------------------
# HOME
# ----------------------------
@app.route("/")
def home():
    return render_template("index.html")

# ----------------------------
# CHAT ENDPOINT
# ----------------------------
@app.route("/ask", methods=["POST"])
def ask():
    data = request.json
    user_input = data.get("message", "").strip()
    session_id = data.get("session_id")

    # init session
    if not session_id or session_id not in sessions:
        session_id = str(uuid.uuid4())
        sessions[session_id] = {
            "messages": []
        }

    session = sessions[session_id]

    # store user message
    session["messages"].append({"role": "user", "content": user_input})

    # build messages
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT}
    ]
    messages.extend(session["messages"][-10:])  # keep last 10 messages only

    # call model
    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=messages,
        max_tokens=600
    )

    reply = response.choices[0].message.content

    # store assistant response
    session["messages"].append({"role": "assistant", "content": reply})

    return jsonify({
        "session_id": session_id,
        "response": reply
    })

# ----------------------------
# RUN
# ----------------------------
if __name__ == "__main__":
    app.run(debug=True)
