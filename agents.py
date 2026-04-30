from openai import OpenAI
import os
import json

client = None

if os.environ.get("OPENAI_API_KEY"):
    try:
        client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
    except Exception as e:
        print("OpenAI init error:", e)
        client = None


def load_kb():
    try:
        with open("knowledge_base.json") as f:
            return json.load(f)
    except Exception as e:
        print("KB load error:", e)
        return []


def match_kb(text, kb):
    text = text.lower()
    matches = []

    for item in kb:
        for k in item.get("keywords", []):
            if k in text:
                matches.extend(item.get("fixes", []))

    return matches


def safe_response(analysis="", fixes=None, category="unknown", confidence=0.5):
    return {
        "analysis": analysis or "No analysis available",
        "category": category,
        "confidence": confidence,
        "fixes": fixes or []
    }


def run_agent(user_input, memory):
    kb = load_kb()
    kb_matches = match_kb(user_input, kb)

    # 🔒 If no AI available → fallback
    if not client:
        return safe_response(
            analysis="AI unavailable. Showing knowledge base suggestions.",
            fixes=kb_matches
        )

    try:
        res = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": """You are an IT troubleshooting assistant.
Return STRICT JSON:
{
  "analysis": "string",
  "category": "string",
  "confidence": number,
  "fixes": [{"id": "string", "label": "string"}]
}"""
                },
                {"role": "user", "content": user_input}
            ],
            response_format={"type": "json_object"}
        )

        raw = res.choices[0].message.content

        try:
            result = json.loads(raw)
        except Exception as parse_error:
            print("JSON parse error:", parse_error)
            print("RAW RESPONSE:", raw)

            return safe_response(
                analysis="AI returned invalid format. Using fallback.",
                fixes=kb_matches
            )

        # Merge KB fixes safely
        merged = {
            f["id"]: f for f in (kb_matches + result.get("fixes", []))
        }

        return safe_response(
            analysis=result.get("analysis"),
            category=result.get("category"),
            confidence=result.get("confidence"),
            fixes=list(merged.values())
        )

    except Exception as e:
        print("AI call error:", str(e))

        return safe_response(
            analysis=f"AI error occurred: {str(e)}",
            fixes=kb_matches
        )
