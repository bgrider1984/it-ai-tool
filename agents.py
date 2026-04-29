from openai import OpenAI
import os
import json

client = None
if os.environ.get("OPENAI_API_KEY"):
    try:
        client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
    except:
        client = None


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

    # 🔥 SAFE FALLBACK if OpenAI unavailable
    if not client:
        return {
            "analysis": "AI unavailable. Showing knowledge base suggestions.",
            "category": "unknown",
            "confidence": 0.5,
            "fixes": kb_matches
        }

    try:
        res = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Return JSON troubleshooting response."},
                {"role": "user", "content": user_input}
            ],
            response_format={"type": "json_object"}
        )

        result = json.loads(res.choices[0].message.content)

        result["fixes"] = list({
            f["id"]: f for f in (kb_matches + result.get("fixes", []))
        }.values())

        return result

    except Exception as e:
        return {
            "analysis": f"AI error: {str(e)}",
            "category": "error",
            "confidence": 0,
            "fixes": kb_matches
        }
