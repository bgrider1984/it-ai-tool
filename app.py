import os
import uuid
from flask import Flask, render_template, request, jsonify
from openai import OpenAI

app = Flask(__name__)

api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise RuntimeError("Missing OPENAI_API_KEY")

client = OpenAI(api_key=api_key)

sessions = {}

SYSTEM_PROMPT = """
You are a Tier 2 IT support engineer.

Be:
- extremely concise
- action-focused
- diagnostic

Return format:

CAUSE: <likely cause>
FIX:
1. <step>
2. <step>

Then optionally provide up to 3 ACTIONS.

ACTIONS RULES:
- Only include real IT actions
- Each action must be short
- Include command or instruction

Example:
ACTIONS:
- Safe Mode: outlook.exe /safe
- Flush DNS: ipconfig /flushdns
"""

@app.route("/")
def home():
    return render_template("index.html")


@app.route("/ask", methods=["POST"])
def ask():
    data = request.json
    user_input = data.get("message", "")
    session_id = data.get("session_id")

    if not session_id or session_id not in sessions:
        session_id = str(uuid.uuid4())
        sessions[session_id] = {"messages": []}

    session = sessions[session_id]
    session["messages"].append({"role": "user", "content": user_input})

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT}
    ]
    messages.extend(session["messages"][-6:])

    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=messages,
        max_tokens=450,
        temperature=0.3
    )

    reply = response.choices[0].message.content

    session["messages"].append({"role": "assistant", "content": reply})

    # ----------------------------
    # SIMPLE ACTION PARSER
    # ----------------------------
    actions = []
    if "ACTIONS" in reply:
        try:
            action_block = reply.split("ACTIONS:")[1].strip().split("\n")
            for line in action_block:
                if "-" in line:
                    parts = line.replace("-", "").strip().split(":")
                    if len(parts) == 2:
                        actions.append({
                            "label": parts[0].strip(),
                            "command": parts[1].strip()
                        })
        except:
            pass

    return jsonify({
        "session_id": session_id,
        "response": reply.split("ACTIONS:")[0].strip(),
        "actions": actions
    })


if __name__ == "__main__":
    app.run(debug=True)
