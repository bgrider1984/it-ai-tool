from flask import Flask, render_template, request, jsonify, session
from openai import OpenAI
import os
import uuid
import json

app = Flask(__name__)
app.secret_key = "change-this-key"

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

# ----------------------------
# SIMPLE MEMORY STORE
# ----------------------------
MEMORY = {}


def get_session_id():
    if "sid" not in session:
        session["sid"] = str(uuid.uuid4())
    return session["sid"]


def get_memory(sid):
    if sid not in MEMORY:
        MEMORY[sid] = {
            "history": [],
            "facts": [],
            "fixes": [],
            "questions": [],
            "confidence": 0.0
        }
    return MEMORY[sid]


def update_memory(sid, result):
    mem = get_memory(sid)

    mem["history"].append(result)
    mem["facts"].extend(result.get("facts", []))
    mem["fixes"].extend(result.get("fixes", []))
    mem["questions"].extend(result.get("questions", []))
    mem["confidence"] = result.get("confidence", mem["confidence"])

    return mem


# ----------------------------
# MULTI-AGENT PROMPTS
# ----------------------------

DIAGNOSER = """
You are a diagnostic AI agent.

Extract:
- root cause reasoning
- observable facts
- category: hardware, software, network, unknown
- confidence 0.0-1.0

Return JSON:
{
  "analysis": "",
  "facts": [],
  "category": "",
  "confidence": 0.0
}
"""

FIXER = """
You are a repair AI agent.

Generate step-by-step fixes based on diagnosis.

Return JSON:
{
  "fixes": []
}
"""

CLARIFIER = """
You are a clarification agent.

If issue is uncertain or confidence < 0.6,
ask helpful follow-up questions.

Return JSON:
{
  "questions": []
}
"""


def call_ai(system, user):
    res = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user}
        ],
        response_format={"type": "json_object"}
    )
    return json.loads(res.choices[0].message.content)


# ----------------------------
# CORE PIPELINE
# ----------------------------
def analyze(text, memory):

    # 1. Diagnose
    diagnosis = call_ai(DIAGNOSER, text)

    # 2. Fixes
    fixes = call_ai(FIXER, json.dumps(diagnosis))

    confidence = diagnosis.get("confidence", 0.5)

    # 3. Clarifying questions (if needed)
    questions = []
    if confidence < 0.6:
        questions = call_ai(CLARIFIER, json.dumps(diagnosis)).get("questions", [])

    return {
        "analysis": diagnosis.get("analysis", ""),
        "facts": diagnosis.get("facts", []),
        "category": diagnosis.get("category", "unknown"),
        "fixes": fixes.get("fixes", []),
        "questions": questions,
        "confidence": confidence
    }


# ----------------------------
# ROUTES
# ----------------------------

@app.route("/")
def home():
    return render_template("dashboard.html")


@app.route("/api/analyze", methods=["POST"])
def api_analyze():
    sid = get_session_id()
    mem = get_memory(sid)

    text = request.json.get("text", "")

    result = analyze(text, mem)

    update_memory(sid, result)

    return jsonify(result)


@app.route("/api/memory")
def memory_dump():
    sid = get_session_id()
    return jsonify(get_memory(sid))


if __name__ == "__main__":
    app.run(debug=True)
