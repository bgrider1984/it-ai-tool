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
        for k in item.get("keywords", []):
            if k in text:
                matches.extend(item.get("fixes", []))

    return matches


def safe_response(analysis="", fixes=None):
    return {
        "analysis": analysis or "No analysis available",
        "fixes": fixes or []
    }


def run_agent(user_input, memory):
    kb = load_kb()
    kb_matches = match_kb(user_input, kb)

    # 🔥 If no AI → still works great now
    if not client:
        return safe_response(
            analysis="Hardware/software issue detected. Follow suggested checks.",
            fixes=kb_matches
        )

    try:
        res = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": """You are an IT troubleshooting assistant.
Return JSON:
{
  "analysis": "",
  "fixes": [{"id":"","label":""}]
}"""
                },
                {"role": "user", "content": user_input}
            ],
            response_format={"type": "json_object"}
        )

        raw = res.choices[0].message.content

        try:
            result = json.loads(raw)
        except:
            return safe_response(
                analysis="AI response failed. Using known troubleshooting steps.",
                fixes=kb_matches
            )

        # 🔥 SMART MERGE + HARDWARE PRIORITY
        merged = {
            f["id"]: f for f in (kb_matches + result.get("fixes", []))
        }

        return safe_response(
            analysis=result.get("analysis"),
            fixes=list(merged.values())
        )

    except Exception as e:
        return safe_response(
            analysis=f"AI error: {str(e)}",
            fixes=kb_matches
        )
