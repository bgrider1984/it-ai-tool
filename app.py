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
- Ask ONE clear troubleshooting question at a time
- Be concise and technical
- Adapt based on previous answers
- When enough information is gathered, provide FINAL_DIAGNOSIS

Format:

If asking a question:
Return ONLY the question.

If ready to resolve:
Start with FINAL_DIAGNOSIS and include:
1. Likely cause
2. Fix steps
3. Commands (if applicable)
4. Prevention tips
"""

# ----------------------------
# SUGGESTION GENERATOR
# ----------------------------
def generate_suggestions(question):
    """
    Creates intelligent common answers for UI buttons.
    """
    q = question.lower()

    if "error" in q:
        return [
            "Yes, I see an error message",
            "No error appears",
            "It closes immediately",
            "Not sure"
        ]

    if "open" in q or "launch" in q:
        return [
            "It won't open at all",
            "It opens then closes",
            "It freezes",
            "Not sure"
        ]

    if "network" in q or "internet" in q:
        return [
            "No internet connection",
            "Slow connection",
            "Intermittent dropouts",
            "Not sure"
        ]

    if "outlook" in q or "email" in q:
        return [
            "Won't open",
            "Not syncing",
            "Error message appears",
            "Not sure"
        ]

    # default safe fallback
    return [
        "Yes",
        "No",
        "Not sure",
        "Other"
    ]

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
    # STORE USER MESSAGE
    # ----------------------------
    session["messages"].append({"role": "user", "content": user_input})

    # ----------------------------
    # AI CALL
    # ----------------------------
    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        max_tokens=500,
        messages=[{"role": "system", "content": SYSTEM_PROMPT}] + session["messages"]
    )

    reply = response.choices[0].message.content

    # ----------------------------
    # CHECK IF FINAL
    # ----------------------------
    is_final = "FINAL_DIAGNOSIS" in reply

    # ----------------------------
    # GENERATE SMART SUGGESTIONS
    # ----------------------------
    suggestions = []

    if not is_final:
        suggestions = generate_suggestions(reply)

    # ----------------------------
    # STORE ASSISTANT RESPONSE
    # ----------------------------
    session["messages"].append({"role": "assistant", "content": reply})

    return jsonify({
        "session_id": session_id,
        "response": reply,
        "options": suggestions,
        "done": is_final
    })


# ----------------------------
# RUN APP
# ----------------------------
if __name__ == "__main__":
    app.run(debug=True)
