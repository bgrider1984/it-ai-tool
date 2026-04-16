import os
import json
from flask import Flask, render_template, request, jsonify
from openai import OpenAI

app = Flask(__name__)

# ----------------------------
# Load API Key (Production-safe)
# ----------------------------
api_key = os.getenv("OPENAI_API_KEY")

if not api_key:
    raise RuntimeError("Missing OPENAI_API_KEY environment variable")

client = OpenAI(api_key=api_key)

# ----------------------------
# Load Knowledge Base
# ----------------------------
try:
    with open("knowledge_base.json", "r") as f:
        knowledge_base = json.load(f)
except Exception:
    knowledge_base = []

def simple_similarity(a, b):
    a_words = set(a.lower().split())
    b_words = set(b.lower().split())
    return len(a_words & b_words) / max(len(a_words), 1)

def find_relevant_knowledge(user_input):
    scored = []

    for item in knowledge_base:
        content = item.get("content", "")
        keywords = " ".join(item.get("keywords", []))

        score = simple_similarity(user_input, keywords + " " + content)

        if score > 0:
            scored.append((score, content))

    scored.sort(reverse=True, key=lambda x: x[0])

    return "\n".join([x[1] for x in scored[:3]])

# ----------------------------
# System Prompt
# ----------------------------
SYSTEM_PROMPT = """
You are a senior enterprise IT support engineer specializing in:

- Windows 10/11
- Active Directory
- Microsoft 365 / Office
- VPN / networking issues
- Enterprise desktop support

Always respond in:

1. Clarifying Questions
2. Likely Causes (ranked)
3. Step-by-Step Troubleshooting
4. Commands (if applicable)
5. Escalation Conditions

Be concise, technical, and action-oriented.

If the user answers previous clarifying questions, continue troubleshooting based on their response instead of repeating questions.
"""
# ----------------------------
# Routes
# ----------------------------
@app.route("/")
def home():
    return render_template("index.html")


@app.route("/ask", methods=["POST"])
@app.route("/ask", methods=["POST"])
def ask():
    try:
        data = request.json
        history = data.get("history", [])

        messages = [{"role": "system", "content": SYSTEM_PROMPT}]

        # Add full conversation history
        for msg in history:
            messages.append({
                "role": msg["role"],
                "content": msg["content"]
            })

        response = client.chat.completions.create(
            model="gpt-4.1-mini",
            max_tokens=400,
            messages=messages
        )

        reply = response.choices[0].message.content

        usage = response.usage
        tokens = usage.total_tokens
        cost = (usage.prompt_tokens * 0.0000004) + (usage.completion_tokens * 0.0000016)

        return jsonify({
            "response": reply,
            "tokens": tokens,
            "cost": round(cost, 6)
        })

    except Exception as e:
        return jsonify({
            "response": "Server error occurred.",
            "error": str(e)
        }), 500


# ----------------------------
# Run locally only
# ----------------------------
if __name__ == "__main__":
    app.run(debug=True)
