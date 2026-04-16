import os
import json
from flask import Flask, render_template, request, jsonify
from openai import OpenAI

app = Flask(__name__)

# ----------------------------
# API KEY
# ----------------------------
api_key = os.getenv("OPENAI_API_KEY")

if not api_key:
    raise RuntimeError("Missing OPENAI_API_KEY environment variable")

client = OpenAI(api_key=api_key)

# ----------------------------
# LOAD KNOWLEDGE BASE (optional)
# ----------------------------
try:
    with open("knowledge_base.json", "r") as f:
        knowledge_base = json.load(f)
except Exception:
    knowledge_base = []

# ----------------------------
# SIMPLE KNOWLEDGE MATCH
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
# SYSTEM PROMPT (HARD LOCKED JSON MODE)
# ----------------------------
SYSTEM_PROMPT = """
You are a senior IT troubleshooting assistant.

You operate in a STRICT decision-tree system.

You MUST ALWAYS return VALID JSON in this format:

{
  "response": "Your question or explanation",
  "options": ["Option 1", "Option 2", "Option 3"]
}

RULES:
- Always ask ONE question at a time
- Always provide 2–4 options when asking a question
- If enough info is collected, provide solution steps and set options to []
- NEVER return plain text
- NEVER break JSON format
- If unsure, still return valid JSON

IMPORTANT:
If the user responds to a previous question, continue the troubleshooting flow.
Do NOT restart or repeat earlier steps.
"""

# ----------------------------
# SAFE JSON PARSER
# ----------------------------
def parse_ai_response(text):
    try:
        return json.loads(text)
    except Exception:
        return {
            "response": text,
            "options": []
        }

# ----------------------------
# ROUTES
# ----------------------------
@app.route("/")
def home():
    return render_template("index.html")


@app.route("/ask", methods=["POST"])
def ask():
    try:
        data = request.json
        history = data.get("history", [])

        # ----------------------------
        # IMPORTANT FIX:
        # Only keep last 2 messages to prevent context drift
        # ----------------------------
        trimmed_history = history[-2:]

        messages = [{"role": "system", "content": SYSTEM_PROMPT}]

        # Add trimmed conversation history
        for msg in trimmed_history:
            messages.append({
                "role": msg["role"],
                "content": msg["content"]
            })

        # Add contextual knowledge from last user message
        if trimmed_history:
            last_user = trimmed_history[-1]["content"]
            knowledge = find_relevant_knowledge(last_user)

            if knowledge:
                messages.append({
                    "role": "system",
                    "content": f"Relevant internal knowledge:\n{knowledge}"
                })

        # ----------------------------
        # OPENAI CALL (STRICT JSON MODE)
        # ----------------------------
        response = client.chat.completions.create(
            model="gpt-4.1-mini",
            max_tokens=400,
            response_format={"type": "json_object"},
            messages=messages
        )

        raw_reply = response.choices[0].message.content

        parsed = parse_ai_response(raw_reply)

        # ----------------------------
        # USAGE TRACKING
        # ----------------------------
        usage = response.usage
        tokens = usage.total_tokens
        cost = (usage.prompt_tokens * 0.0000004) + (usage.completion_tokens * 0.0000016)

        return jsonify({
            "response": parsed.get("response", ""),
            "options": parsed.get("options", []),
            "tokens": tokens,
            "cost": round(cost, 6)
        })

    except Exception as e:
        return jsonify({
            "response": "Server error occurred.",
            "options": [],
            "error": str(e)
        }), 500


# ----------------------------
# RUN APP
# ----------------------------
if __name__ == "__main__":
    app.run(debug=True)
