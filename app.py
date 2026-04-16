import os
import json
from flask import Flask, render_template, request, jsonify
from openai import OpenAI

app = Flask(__name__)

# ----------------------------
# Load API Key
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

# ----------------------------
# Smart Knowledge Matching
# ----------------------------
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
# System Prompt (GUIDED MODE)
# ----------------------------
SYSTEM_PROMPT = """
You are a senior IT troubleshooting assistant.

You guide users step-by-step like a decision tree.

ALWAYS respond in JSON format:

{
  "response": "Your explanation or question",
  "options": ["Option 1", "Option 2", "Option 3"]
}

Rules:
- Ask ONE focused troubleshooting question at a time
- Provide 2–4 clear answer options
- Options should help narrow down the issue
- If enough info is gathered, provide solution steps instead of options
- If giving final solution, options can be empty []
- Never return plain text — always JSON
"""

# ----------------------------
# Parse AI Response
# ----------------------------
def parse_ai_response(text):
    try:
        return json.loads(text)
    except:
        return {
            "response": text,
            "options": []
        }

# ----------------------------
# Routes
# ----------------------------
@app.route("/")
def home():
    return render_template("index.html")


@app.route("/ask", methods=["POST"])
def ask():
    try:
        data = request.json
        history = data.get("history", [])

        messages = [{"role": "system", "content": SYSTEM_PROMPT}]

        # Add conversation history
        for msg in history:
            messages.append({
                "role": msg["role"],
                "content": msg["content"]
            })

        # Add knowledge (based on last user message)
        if history:
            last_user = history[-1]["content"]
            knowledge = find_relevant_knowledge(last_user)

            messages.append({
                "role": "system",
                "content": f"Relevant internal knowledge:\n{knowledge}"
            })

        response = client.chat.completions.create(
            model="gpt-4.1-mini",
            max_tokens=400,
            messages=messages
        )

        raw_reply = response.choices[0].message.content
        parsed = parse_ai_response(raw_reply)

        usage = response.usage
        tokens = usage.total_tokens
        cost = (usage.prompt_tokens * 0.0000004) + (usage.completion_tokens * 0.0000016)

        return jsonify({
            "response": parsed.get("response"),
            "options": parsed.get("options", []),
            "tokens": tokens,
            "cost": round(cost, 6)
        })

    except Exception as e:
        return jsonify({
            "response": "Server error occurred.",
            "error": str(e)
        }), 500


# ----------------------------
# Run Local
# ----------------------------
if __name__ == "__main__":
    app.run(debug=True)
