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
# CONFUSION DETECTION
# ----------------------------
def detect_confusion(messages):
    recent = messages[-4:]
    text = " ".join([m["content"].lower() for m in recent if m["role"] == "user"])

    triggers = [
        "not sure",
        "doesn't work",
        "didn't work",
        "still broken",
        "no idea",
        "same issue"
    ]

    return sum(1 for t in triggers if t in text) >= 2

# ----------------------------
# SKILL CLASSIFICATION
# ----------------------------
def calculate_skill(level_score):
    if level_score < -2:
        return "beginner"
    elif level_score < 3:
        return "intermediate"
    else:
        return "advanced"

# ----------------------------
# SYSTEM PROMPT
# ----------------------------
SYSTEM_PROMPT = """
You are a senior IT engineer mentoring a junior technician.

You adapt your teaching style based on user skill level:

BEGINNER:
- Very simple steps
- Extra explanation
- Slow progression

INTERMEDIATE:
- Normal troubleshooting flow
- Light explanation

ADVANCED:
- Minimal explanation
- Fast diagnostic steps

Rules:
- ONE step at a time
- NEVER overwhelm the user
- Always wait for user response
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
            "messages": [],
            "skill_score": 0,
            "skill": "beginner"
        }

    session = sessions[session_id]

    # ----------------------------
    # STORE USER MESSAGE
    # ----------------------------
    session["messages"].append({"role": "user", "content": user_input})

    # ----------------------------
    # CONFUSION CHECK
    # ----------------------------
    confused = detect_confusion(session["messages"])

    # ----------------------------
    # UPDATE SKILL SCORE
    # ----------------------------
    if confused:
        session["skill_score"] -= 1
    else:
        session["skill_score"] += 1

    session["skill"] = calculate_skill(session["skill_score"])

    # ----------------------------
    # ADAPT BEHAVIOR BY SKILL
    # ----------------------------
    skill_instruction = ""

    if session["skill"] == "beginner":
        skill_instruction = "USER IS BEGINNER: explain simply and slowly."
    elif session["skill"] == "intermediate":
        skill_instruction = "USER IS INTERMEDIATE: normal troubleshooting pace."
    else:
        skill_instruction = "USER IS ADVANCED: be concise and technical."

    # ----------------------------
    # ADD CONFUSION OVERRIDE
    # ----------------------------
    if confused:
        skill_instruction += """
USER IS CONFUSED:
- Slow down
- Re-explain last step more clearly
- Ask ONE clarifying question only
"""

    # ----------------------------
    # BUILD CONTEXT
    # ----------------------------
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT + "\n" + skill_instruction}
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
        "skill": session["skill"],
        "skill_score": session["skill_score"],
        "confused": confused
    })


# ----------------------------
# RUN APP
# ----------------------------
if __name__ == "__main__":
    app.run(debug=True)
