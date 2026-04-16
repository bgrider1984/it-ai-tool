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

    triggers = ["not sure", "didn't work", "still broken", "no idea"]
    return sum(1 for t in triggers if t in text) >= 2

# ----------------------------
# TOPIC DETECTION
# ----------------------------
def detect_topic(text):
    text = text.lower()

    topics = {
        "outlook": ["outlook", "email", "mail"],
        "network": ["wifi", "internet", "vpn", "dns"],
        "windows": ["windows", "login", "boot"],
        "software": ["crash", "freeze", "app"],
        "printer": ["printer", "print"]
    }

    for k, v in topics.items():
        if any(x in text for x in v):
            return k

    return "general"

# ----------------------------
# UPDATE WEAK AREAS
# ----------------------------
def update_weak(session, topic, confused):
    if "weak_areas" not in session:
        session["weak_areas"] = {}

    session["weak_areas"][topic] = session["weak_areas"].get(topic, 0)

    if confused:
        session["weak_areas"][topic] -= 1
    else:
        session["weak_areas"][topic] += 1

# ----------------------------
# SKILL LEVEL
# ----------------------------
def skill_level(score):
    if score < -2:
        return "beginner"
    elif score < 3:
        return "intermediate"
    return "advanced"

# ----------------------------
# SYSTEM PROMPT
# ----------------------------
SYSTEM_PROMPT = """
You are an IT support coach.

Rules:
- One step at a time
- Adapt to skill + weak areas
- Keep concise and practical
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

    if not session_id or session_id not in sessions:
        session_id = str(uuid.uuid4())
        sessions[session_id] = {
            "messages": [],
            "score": 0,
            "weak_areas": {},
            "events": []
        }

    s = sessions[session_id]

    s["messages"].append({"role": "user", "content": user_input})

    confused = detect_confusion(s["messages"])
    topic = detect_topic(user_input)

    # skill score
    if confused:
        s["score"] -= 1
    else:
        s["score"] += 1

    level = skill_level(s["score"])

    update_weak(s, topic, confused)

    weak_sorted = sorted(s["weak_areas"].items(), key=lambda x: x[1])
    weak_list = [w[0] for w in weak_sorted[:3]]

    # track events for dashboard
    s["events"].append({
        "score": s["score"],
        "level": level,
        "confused": confused
    })

    messages = [
        {
            "role": "system",
            "content": SYSTEM_PROMPT +
            f"\nSkill: {level}\nWeak areas: {', '.join(weak_list)}"
        }
    ]

    messages.extend(s["messages"])

    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=messages,
        max_tokens=700
    )

    reply = response.choices[0].message.content

    s["messages"].append({"role": "assistant", "content": reply})

    return jsonify({
        "session_id": session_id,
        "response": reply,
        "skill": level,
        "score": s["score"],
        "weak_areas": weak_list,
        "confused": confused
    })

# ----------------------------
# DASHBOARD ENDPOINT
# ----------------------------
@app.route("/dashboard", methods=["POST"])
def dashboard():
    data = request.json
    session_id = data.get("session_id")

    if not session_id or session_id not in sessions:
        return jsonify({"error": "invalid session"}), 400

    s = sessions[session_id]

    weak_sorted = sorted(s["weak_areas"].items(), key=lambda x: x[1])

    return jsonify({
        "score_history": s["events"],
        "weak_areas": weak_sorted,
        "total_messages": len(s["messages"])
    })

# ----------------------------
# RUN
# ----------------------------
if __name__ == "__main__":
    app.run(debug=True)
