import os
import uuid
from flask import Flask, render_template, request, jsonify
from openai import OpenAI

app = Flask(__name__)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

sessions = {}

# ----------------------------
# SESSION INIT
# ----------------------------
def get_session(session_id):
    if not session_id or session_id not in sessions:
        session_id = str(uuid.uuid4())
        sessions[session_id] = {
            "steps": [],
            "current_index": 0,
            "step_results": {},
            "history": []
        }
    return session_id, sessions[session_id]

# ----------------------------
# AI ENGINE (STRUCTURED STEPS)
# ----------------------------
def generate_plan(message, history):

    prompt = f"""
You are a Tier 2 IT troubleshooting engineer.

Create an EXECUTABLE troubleshooting plan.

Rules:
- Steps must be actionable
- Each step must be independent
- Include clear instructions
- Order from easiest → hardest fix

Return ONLY JSON:

{{
  "issue": "short description",
  "steps": [
    {{
      "id": "unique_step_id",
      "title": "step name",
      "instructions": "exact actions user performs",
      "expected": "what should happen"
    }}
  ]
}}

Issue:
{message}

History:
{history}
"""

    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
        max_tokens=700
    )

    return response.choices[0].message.content

# ----------------------------
# STEP EVALUATION ENGINE
# ----------------------------
def evaluate_next_step(session):

    steps = session["steps"]
    idx = session["current_index"]

    # skip completed steps
    while idx < len(steps):
        step_id = steps[idx]["id"]
        if session["step_results"].get(step_id) == "failed":
            idx += 1
            continue
        break

    session["current_index"] = idx

    if idx >= len(steps):
        return None

    return steps[idx]

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

    session_id, session = get_session(session_id)

    session["history"].append(message)

    raw = generate_plan(message, session["history"])

    try:
        plan = eval(raw.replace("null", "None"))
    except:
        plan = {"issue": "error", "steps": []}

    session["steps"] = plan.get("steps", [])
    session["current_index"] = 0
    session["step_results"] = {}

    next_step = evaluate_next_step(session)

    return jsonify({
        "session_id": session_id,
        "issue": plan.get("issue"),
        "step": next_step,
        "all_steps": session["steps"]
    })


# ----------------------------
# STEP FEEDBACK ENDPOINT
# ----------------------------
@app.route("/step", methods=["POST"])
def step_feedback():

    data = request.json
    session_id = data.get("session_id")
    step_id = data.get("step_id")
    result = data.get("result")  # passed / failed

    session = sessions.get(session_id)

    if not session:
        return jsonify({"error": "no session"}), 400

    session["step_results"][step_id] = result

    if result == "passed":
        session["current_index"] += 1

    next_step = evaluate_next_step(session)

    return jsonify({
        "next_step": next_step
    })


if __name__ == "__main__":
    app.run(debug=True)
