from dotenv import load_dotenv
load_dotenv()
print("KEY LOADED:", os.getenv("OPENAI_API_KEY"))

from flask import Flask, render_template, request, jsonify
from openai import OpenAI
import json
import os

load_dotenv()

app = Flask(__name__)

# ----------------------------
# OpenAI Client (Modern SDK)
# ----------------------------
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

# ----------------------------
# Load Knowledge Base
# ----------------------------
try:
    with open("knowledge_base.json", "r") as f:
        knowledge_base = json.load(f)
except:
    knowledge_base = []

def find_relevant_knowledge(user_input):
    user_input = user_input.lower()
    matches = []

    for item in knowledge_base:
        for keyword in item.get("keywords", []):
            if keyword in user_input:
                matches.append(item.get("content", ""))

    return "\n".join(matches[:3])  # limit to top 3 matches

# ----------------------------
# System Prompt (IT Copilot Behavior)
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
    try:
        user_input = request.json.get("message", "")

        # 🔍 Get relevant knowledge
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

        # 🤖 OpenAI call
        response = client.chat.completions.create(
            model="gpt-4.1-mini",
            max_tokens=400,
            messages=messages
        )

        reply = response.choices[0].message.content

        # 📊 Token usage
        usage = response.usage
        prompt_tokens = usage.prompt_tokens
        completion_tokens = usage.completion_tokens
        total_tokens = usage.total_tokens

        # 💰 Cost calculation (approx)
        input_cost = prompt_tokens * 0.0000004
        output_cost = completion_tokens * 0.0000016
        total_cost = input_cost + output_cost

        print(f"Tokens: {total_tokens} | Cost: ${total_cost:.6f}")

        return jsonify({
            "response": reply,
            "tokens": total_tokens,
            "cost": round(total_cost, 6)
        })

    except Exception as e:
        print("ERROR:", str(e))
        return jsonify({
            "response": f"Server Error: {str(e)}"
        }), 500

# ----------------------------
# Run App
# ----------------------------
if __name__ == "__main__":
    app.run(debug=True)
