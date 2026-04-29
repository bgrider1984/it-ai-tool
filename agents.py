from openai import OpenAI
import os
import json

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
MODEL = "gpt-4o-mini"


SYSTEM = """
You are an advanced IT troubleshooting AI.

You can:
- Diagnose issues
- Suggest fixes
- Decide when to run diagnostics
- Suggest safe auto-fixes

Available tools:
- network_check
- ip_config
- usb_devices
- disk_space
- cpu_usage

Available auto-fix actions:
- reset_network
- flush_dns
- restart_adapter

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
  "auto_fix": "",
  "confidence": 0.0
}

Rules:
- Only suggest auto_fix if confidence > 0.7
- Prefer diagnostics before fixes
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

    # Merge KB fixes
    if matches:
        kb_fixes = []
        for m in matches:
            kb_fixes.extend(m["fixes"])

        result["fixes"] = list(dict.fromkeys(kb_fixes + result.get("fixes", [])))
        result["confidence"] = min(1.0, result.get("confidence", 0.5) + 0.2)

    return result
