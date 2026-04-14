from flask import Flask, render_template, request, jsonify
import openai
import json
import os

app = Flask(__name__)

# 🔑 OpenAI key from Render environment variables
openai.api_key = os.environ.get("OPENAI_API_KEY")

# ----------------------------
# Load Knowledge Base
# ----------------------------
with open("knowledge_base.json", "r") as f:
    knowledge_base = json.load(f)

def find_relevant_knowledge(user_input):
    user_input = user_input.lower()
    matches = []

    for item in knowledge_base:
        for keyword in item["keywords"]:
            if keyword in user_input:
                matches.append(item["content"])

    return "\n".join(matches[:3])  # top 3 matches

# ----------------------------
# System Prompt (CORE BEHAVIOR)
# ----------------------------
SYSTEM_PROMPT = """
You are a senior enterprise IT support engineer specializing in:

- Windows 10/11
- Active Directory
- Microsoft 365 / Office
- VPN / networking issues
- Enterprise desktop support

You troubleshoot like a Tier 2/3 engineer.

Always respond in this structure:

1. Clarifying Questions
2. Likely Causes (ranked)
3. Step-by-Step Troubleshooting
4. Commands (if applicable)
5. Escalation Conditions

Be concise, technical, and action-oriented.
Avoid generic advice.
"""

# ----------------------------
# Routes
# ----------------------------
@app.route("/")
def home():
    return render_template("index.html")


@app.route("/ask", methods=["POST"])
def ask():
    user_input = request.json["message"]

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

    response = openai.ChatCompletion.create(
        model="gpt-4o-mini",
        messages=messages
    )

    return jsonify({
        "response": response["choices"][0]["message"]["content"]
    })


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
