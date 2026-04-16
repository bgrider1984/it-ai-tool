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
# SYSTEM PROMPT
# ----------------------------
SYSTEM_PROMPT = """
You are an enterprise IT troubleshooting assistant.

Your job:
- Ask ONE clear question at a time OR provide a fix step
- Keep responses short and actionable
- Adapt based on conversation history
- Do NOT use multiple-choice options
- Do NOT format responses as forms

When issue is fully diagnosed:
Start with FINAL_DIAGNOSIS:
1. Likely cause
2. Fix steps
3. Commands (if applicable)
4. Prevention tips
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
    # AI CALL
    # ----------------------------
    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        max_tokens=600,
        messages=[{"role": "system", "content": SYSTEM_PROMPT}] + session["messages"]
    )

    reply = response.choices[0].message.content

    # ----------------------------
    # STORE ASSISTANT MESSAGE
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
