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

def find_relevant_knowledge(user_input):
    user_input = user_input.lower()
    matches = []

    for item in knowledge_base:
        for keyword in item.get("keywords", []):
            if keyword in user_input:
                matches.append(item.get("content", ""))

    return "\n".join(matches[:3])

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
"""

# ----------------------------
# Routes
# ----------------------------
@app.route("/")
def home():
    return render_template("index.html")


@app.route("/ask", methods=["POST"])
def ask():
    try:
        user_input = request.json.get("message", "")

        knowledge = find_relevant_knowledge(user_input)

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"""
User Issue:
{user_input}

Relevant Internal Knowledge:
{knowledge}
"""
            }
        ]

        response = client.chat.completions.create(
            model="gpt-4.1-mini",
            max_tokens=400,
            messages=messages
        )

        reply = response.choices[0].message.content

        # ----------------------------
        # Usage tracking
        # ----------------------------
        usage = response.usage
        tokens = usage.total_tokens

        # rough cost estimate
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
