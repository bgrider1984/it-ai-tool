import os
import uuid
from flask import Flask, request, jsonify, session, render_template
from openai import OpenAI

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "dev-secret")

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ----------------------------
# MEMORY
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
# SYSTEM PROMPT (THE BRAIN)
# ----------------------------
SYSTEM_PROMPT = """
You are an expert IT Helpdesk Copilot.

Your job is to guide a junior technician step-by-step through troubleshooting.

RULES:
- Always start simple (restart, power, connections)
- Ask ONE clear question at a time
- If multiple questions are needed, list them clearly
- Always explain HOW to perform each step
- Never jump to advanced solutions too early
- Never repeat the same question unless reworded
- Adapt based on user answers
- If the issue is resolved, acknowledge it and stop
- If not resolved, ALWAYS provide the next step
- Never leave the user without a question or next action

STYLE:
- Clear
- Structured
- Practical
- Like a real helpdesk technician

FORMAT:

Step X:
What to do:
• step instructions

Why:
• explanation

Then ask:
A direct question to continue troubleshooting
"""

# ----------------------------
# AI ENGINE
# ----------------------------
def ai_response(history, user_msg):

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    # include history (last 10 messages)
    for m in history[-10:]:
        messages.append(m)

    messages.append({"role": "user", "content": user_msg})

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        temperature=0.3
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
        msg = request.json.get("message")

        user = get_user()

        # store user message
        user["history"].append({"role": "user", "content": msg})

        reply = ai_response(user["history"], msg)

        # store AI reply
        user["history"].append({"role": "assistant", "content": reply})

        return jsonify({"response": reply})

    except Exception as e:
        print("ERROR:", e)
        return jsonify({
            "response": "⚠ AI error. Check API key or logs."
        }), 500

@app.route("/reset", methods=["POST"])
def reset():
    user = get_user()
    user["history"] = []
    return jsonify({"status":"reset"})

@app.route("/health")
def health():
    return jsonify({
        "status": "ok",
        "openai": bool(os.getenv("OPENAI_API_KEY"))
    })

# ----------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
