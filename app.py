import os
import uuid
from flask import Flask, request, jsonify, session, render_template
from openai import OpenAI

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "dev-secret")

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ----------------------------
# SESSION MEMORY
# ----------------------------
users = {}

def get_user():
    if "uid" not in session:
        session["uid"] = str(uuid.uuid4())

    uid = session["uid"]

    if uid not in users:
        users[uid] = {
            "history": []
        }

    return users[uid]

# ----------------------------
# SMART SYSTEM PROMPT (V8 BRAIN)
# ----------------------------
SYSTEM_PROMPT = """
You are Smart Helpdesk Copilot v8.

You are an IT Tier-1 + Tier-2 troubleshooting assistant.

You MUST:

1. Identify issue type:
   - hardware
   - software
   - network
   - unknown

2. Provide:
   - Likely cause (top 1–3)
   - Step-by-step fix (simple → advanced)
   - ONE question at a time

3. Always include:
   - Next best action
   - Simple instructions first (KISS principle)
   - No repetition of same question twice

4. Output format:

---
🧠 Diagnosis:
- Category:
- Likely cause:

🟢 Quick Fix:
- (1–3 immediate actions user can try)

🔧 Step:
- Clear instruction

❓ Question:
- One direct follow-up question

---

5. NEVER end without a question or next step.
"""

# ----------------------------
# AI ENGINE
# ----------------------------
def generate_response(history, msg):

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    for m in history[-12:]:
        messages.append(m)

    messages.append({"role": "user", "content": msg})

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        temperature=0.4
    )

    return response.choices[0].message.content

# ----------------------------
# ROUTES
# ----------------------------
@app.route("/")
def home():
    return render_template("dashboard.html")

@app.route("/ask", methods=["POST"])
def ask():
    try:
        msg = request.json.get("message", "").strip()

        user = get_user()

        user["history"].append({"role": "user", "content": msg})

        reply = generate_response(user["history"], msg)

        user["history"].append({"role": "assistant", "content": reply})

        return jsonify({
            "response": reply,
            "quick_actions": [
                "Restart device",
                "Check cables",
                "Restart router",
                "Check Task Manager",
                "Update drivers"
            ]
        })

    except Exception as e:
        print("ERROR:", e)
        return jsonify({
            "response": "⚠ System error occurred. Please try again."
        }), 500

@app.route("/reset", methods=["POST"])
def reset():
    user = get_user()
    user["history"] = []
    return jsonify({"status": "reset"})

@app.route("/health")
def health():
    return jsonify({
        "status": "ok",
        "model": "v8-smart-helpdesk"
    })

# ----------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
