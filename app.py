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
# SYSTEM PROMPT (CORE ENGINE)
# ----------------------------
SYSTEM_PROMPT = """
You are an enterprise IT troubleshooting assistant.

Your job:
- Diagnose IT issues step-by-step
- Ask ONLY one question at a time
- Adapt dynamically based on user responses
- Avoid repeating questions
- Stop asking questions when enough information is collected

When you have enough information, respond with:
FINAL_DIAGNOSIS:
then provide:
1. Likely cause
2. Step-by-step fix
3. Commands (if applicable)
4. Prevention tips

Rules:
- Be concise
- Be technical
- Never ask irrelevant questions
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
    # ADD USER MESSAGE
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
        max_tokens=600,
        messages=messages
    )

    reply = response.choices[0].message.content

    # ----------------------------
    # STORE ASSISTANT RESPONSE
    # ----------------------------
    session["messages"].append({"role": "assistant", "content": reply})

    # ----------------------------
    # DETECT FINAL DIAGNOSIS
    # ----------------------------
    is_final = "FINAL_DIAGNOSIS" in reply

    return jsonify({
        "session_id": session_id,
        "response": reply,
        "done": is_final
    })


# ----------------------------
# RUN APP
# ----------------------------
if __name__ == "__main__":
    app.run(debug=True)
