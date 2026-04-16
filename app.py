import os
import uuid
from flask import Flask, render_template, request, jsonify
from openai import OpenAI

app = Flask(__name__)
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

sessions = {}

# ----------------------------
# SESSION
# ----------------------------
def get_session(session_id):
    if not session_id or session_id not in sessions:
        session_id = str(uuid.uuid4())
        sessions[session_id] = {
            "history": [],
            "context": None
        }
    return session_id, sessions[session_id]

# ----------------------------
# CONTEXT-AWARE AI ENGINE
# ----------------------------
def generate_response(message, context, history):

    prompt = f"""
You are a FAST Tier 2 IT Help Desk Copilot.

You may be given a context hint to improve accuracy.

Context hint: {context}

RULES:
- Be concise
- Prioritize fastest fix first
- Max 3–5 steps
- Format as:
  🔴 Try this first
  🟡 If that doesn't work
  🔵 If still broken

Issue:
{message}

History:
{history}
"""

    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
        max_tokens=500
    )

    return response.choices[0].message.content

# ----------------------------
# ROUTES
# ----------------------------
@app.route("/")
def home():
    return render_template("index.html")

@app.route("/ask", methods=["POST"])
def ask():

    data = request.json

    session_id = data.get("session_id")
    message = data.get("message", "")
    context = data.get("context", None)

    session_id, session = get_session(session_id)

    session["history"].append(message)

    # store context if provided
    if context:
        session["context"] = context

    reply = generate_response(
        message=message,
        context=session["context"],
        history=session["history"]
    )

    return jsonify({
        "session_id": session_id,
        "response": reply
    })


if __name__ == "__main__":
    app.run(debug=True)
