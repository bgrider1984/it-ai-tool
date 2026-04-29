from openai import OpenAI
import os
import json

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

SYSTEM = """
You are an IT troubleshooting AI.

Return JSON:

{
  "analysis": "",
  "category": "",
  "confidence": 0.0,
  "fixes": [
    {"id": "", "label": ""}
  ]
}

Only use known fix IDs if relevant:
- flush_dns
- reset_network
- check_cpu
"""


def load_kb():
    try:
        with open("knowledge_base.json") as f:
            return json.load(f)
    except:
        return []


def match_kb(text, kb):
    text = text.lower()
    matches = []

    for item in kb:
        for k in item["keywords"]:
            if k in text:
                matches.extend(item["fixes"])

    return matches


def run_agent(user_input, memory):
    kb = load_kb()
    kb_matches = match_kb(user_input, kb)

    res = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": user_input}
        ],
        response_format={"type": "json_object"}
    )

    result = json.loads(res.choices[0].message.content)

    # Merge KB fixes
    result["fixes"] = list({
        f["id"]: f for f in (kb_matches + result.get("fixes", []))
    }.values())

    return result
