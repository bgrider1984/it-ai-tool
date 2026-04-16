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
# SYSTEM PROMPT (CONTROLLED AI)
# ----------------------------
SYSTEM_PROMPT = """
You are an enterprise IT troubleshooting assistant.

Your job:
- Ask one focused troubleshooting question at a time
- ALWAYS include multiple-choice options (4 max)
- Always include "Not sure" as the last option
- Keep options short and actionable
- Do NOT ask open-ended questions

When enough information is collected, respond with:

FINAL_DIAGNOSIS:
1. Likely cause
2. Step-by-step fix
3. Commands if applicable
4. Prevention tips

Rules:
- Be concise
- Be technical but simple
- Never repeat the same question
"""

# ----------------------------
# HOME
# ----------------------------
@app.route("/")
def home():
    return render_template("index.html")

# ----------------------------
# HELPERS
# ----------------------------
def extract_options(text):
    """
    Ensures UI always gets options.
    If AI forgets, we safely fallback.
    """
    return ["Not sure"]

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
    # STORE USER INPUT
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
        max_tokens=500,
        messages=messages
    )

    reply = response.choices[0].message.content

    # ----------------------------
    # DETECT FINAL ANSWER
    # ----------------------------
    is_final = "FINAL_DIAGNOSIS" in reply

    # ----------------------------
    # GENERATE SAFE OPTIONS
    # ----------------------------
    options = []

    if not is_final:
        # Ask AI to propose options (second lightweight call avoided for cost)
        # We infer simple safe defaults based on question type

        if "error" in reply.lower():
            options = [
                "Yes",
                "No",
                "Not sure"
            ]
        elif "network" in reply.lower():
            options = [
                "WiFi issue",
                "No internet",
                "Slow connection",
                "Not sure"
            ]
        elif "outlook" in reply.lower() or "email" in reply.lower():
            options = [
                "Won't open",
                "Not syncing",
                "Error message",
                "Not sure"
            ]
        else:
            options = [
                "Yes",
                "No",
                "Not sure"
            ]

    # ----------------------------
    # STORE ASSISTANT RESPONSE
    # ----------------------------
    session["messages"].append({"role": "assistant", "content": reply})

    return jsonify({
        "session_id": session_id,
        "response": reply,
        "options": options,
        "done": is_final
    })


# ----------------------------
# RUN APP
# ----------------------------
if __name__ == "__main__":
    app.run(debug=True)
