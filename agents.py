from openai import OpenAI
import os
import json

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
MODEL = "gpt-4o-mini"


SYSTEM = """
You are an autonomous IT troubleshooting AI.

You will be given:
- user input
- previous memory
- optional knowledge base matches

Your job:
- Diagnose the issue
- Merge AI reasoning with known fixes if relevant
- Prefer known fixes when confidence is high

Return JSON:

{
  "analysis": "",
  "facts": [],
  "category": "",
  "fixes": [],
  "tool": {
    "name": "",
    "input": {}
  },
  "confidence": 0.0
}
"""


def load_kb():
    try:
        with open("knowledge_base.json", "r") as f:
            return json.load(f)
    except:
        return []


def match_kb(user_input, kb):
    matches = []

    text = user_input.lower()

    for item in kb:
        for keyword in item["keywords"]:
            if keyword in text:
                matches.append(item)

    return matches


def run_agent(user_input, memory):
    kb = load_kb()
    matches = match_kb(user_input, kb)

    payload = {
        "input": user_input,
        "memory": memory,
        "kb_matches": matches
    }

    res = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": json.dumps(payload)}
        ],
        response_format={"type": "json_object"}
    )

    result = json.loads(res.choices[0].message.content)

    # 🔥 Boost confidence if KB matched
    if matches:
        result["confidence"] = min(1.0, result.get("confidence", 0.5) + 0.2)

        # Merge KB fixes
        kb_fixes = []
        for m in matches:
            kb_fixes.extend(m["fixes"])

        # Avoid duplicates
        result["fixes"] = list(dict.fromkeys(kb_fixes + result.get("fixes", [])))

    return result
