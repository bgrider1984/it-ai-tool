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
# DETECT CONFUSION
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
        "same issue",
        "nothing happens"
    ]

    return sum(1 for t in triggers if t in text) >= 2

# ----------------------------
# DETECT TOPIC (WEAK AREA CLASSIFICATION)
# ----------------------------
def detect_topic(user_input):
    text = user_input.lower()

    topics = {
        "outlook": ["outlook", "email", "mail", "smtp", "exchange"],
        "network": ["wifi", "internet", "network", "vpn", "dns"],
        "windows": ["windows", "login", "boot", "startup", "profile"],
        "software": ["crash", "freeze", "app", "application", "program"],
        "printer": ["printer", "print", "printing", "spooler"]
    }

    for topic, keywords in topics.items():
        if any(k in text for k in keywords):
            return topic

    return "general"

# ----------------------------
# UPDATE WEAK AREAS
# ----------------------------
def update_weak_areas(session, topic, confused):
    if "weak_areas" not in session:
        session["weak_areas"] = {}

    if topic not in session["weak_areas"]:
        session["weak_areas"][topic] = 0

    # increase weakness if confused
    if confused:
        session["weak_areas"][topic] -= 1
    else:
        session["weak_areas"][topic] += 1

# ----------------------------
# SKILL CALCULATION
# ----------------------------
def calculate_skill(score):
    if score < -2:
        return "beginner"
    elif score < 3:
        return "intermediate"
    return "advanced"

# ----------------------------
# SYSTEM PROMPT
# ----------------------------
SYSTEM_PROMPT = """
You are a senior IT engineer mentoring a junior technician.

Rules:
- One step at a time
- Clear and practical instructions
- Adapt to user skill level and weak areas
- Do not overwhelm user

Format:
1. What I think is happening
2. One next step
3. What to observe
4. Next direction if it fails
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
            "skill": "beginner",
            "weak_areas": {}
        }

    session = sessions[session_id]

    # ----------------------------
    # DETECT CONFUSION + TOPIC
    # ----------------------------
    session["messages"].append({"role": "user", "content": user_input})

    confused = detect_confusion(session["messages"])
    topic = detect_topic(user_input)

    # ----------------------------
    # UPDATE SKILL
    # ----------------------------
    if confused:
        session["skill_score"] -= 1
    else:
        session["skill_score"] += 1

    session["skill"] = calculate_skill(session["skill_score"])

    # ----------------------------
    # UPDATE WEAK AREAS
    # ----------------------------
    update_weak_areas(session, topic, confused)

    weak_areas_sorted = sorted(
        session["weak_areas"].items(),
        key=lambda x: x[1]
    )

    weak_area_list = [w[0] for w in weak_areas_sorted[:3]]

    # ----------------------------
    # ADAPT BEHAVIOR
    # ----------------------------
    skill_instruction = f"""
USER SKILL: {session['skill']}
WEAK AREAS: {', '.join(weak_area_list) if weak_area_list else 'None detected yet'}

Adjust explanation based on weak areas.
If issue matches weak area, slow down and simplify.
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

    session["messages"].append({"role": "assistant", "content": reply})

    return jsonify({
        "session_id": session_id,
        "response": reply,
        "skill": session["skill"],
        "skill_score": session["skill_score"],
        "confused": confused,
        "weak_areas": weak_area_list
    })


# ----------------------------
# RUN APP
# ----------------------------
if __name__ == "__main__":
    app.run(debug=True)
