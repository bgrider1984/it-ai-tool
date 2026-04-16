import os
import uuid
import time
from flask import Flask, render_template, request, jsonify
from openai import OpenAI

app = Flask(__name__)
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ----------------------------
# SAAS USERS (replace later with DB)
# ----------------------------
USERS = {
    "demo-key-123": {
        "name": "Demo User",
        "plan": "free",
        "requests": []
    }
}

# ----------------------------
# SESSIONS
# ----------------------------
SESSIONS = {}

# ----------------------------
# RATE LIMIT CONFIG
# ----------------------------
LIMIT_PER_MINUTE = 30

def rate_limit(user):
    now = time.time()
    window = 60

    user["requests"] = [t for t in user["requests"] if now - t < window]

    if len(user["requests"]) >= LIMIT_PER_MINUTE:
        return False

    user["requests"].append(now)
    return True

# ----------------------------
# GET USER
# ----------------------------
def get_user(api_key):
    return USERS.get(api_key)

# ----------------------------
# SESSION
# ----------------------------
def get_session(session_id):
    if not session_id or session_id not in SESSIONS:
        session_id = str(uuid.uuid4())
        SESSIONS[session_id] = {
            "history": []
        }
    return session_id, SESSIONS[session_id]

# ----------------------------
# CORE AI ENGINE
# ----------------------------
def generate_response(message, history):

    prompt = f"""
You are a FAST Tier 2 IT Copilot for junior technicians.

Rules:
- Be extremely concise
- First give MOST likely fix
- Then 2-4 backup steps
- No fluff

Format:

🔴 Most likely fix:
🟡 If that doesn't work:
🔵 If still broken:

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

    api_key = data.get("api_key")
    message = data.get("message", "")
    session_id = data.get("session_id")

    user = get_user(api_key)

    if not user:
        return jsonify({"error": "Invalid API key"}), 403

    if not rate_limit(user):
        return jsonify({"error": "Rate limit exceeded"}), 429

    session_id, session = get_session(session_id)

    session["history"].append(message)

    response = generate_response(message, session["history"])

    return jsonify({
        "session_id": session_id,
        "response": response,
        "plan": user["plan"]
    })


# ----------------------------
# SIMPLE USAGE STATS (FOR SAAS)
# ----------------------------
@app.route("/stats", methods=["POST"])
def stats():

    api_key = request.json.get("api_key")
    user = get_user(api_key)

    if not user:
        return jsonify({"error": "invalid"}), 403

    return jsonify({
        "requests_used": len(user["requests"]),
        "plan": user["plan"]
    })


if __name__ == "__main__":
    app.run(debug=True)
