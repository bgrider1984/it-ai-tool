from openai import OpenAI
import os
import json

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

MODEL = "gpt-4o-mini"


DIAGNOSER = """
You are a senior IT diagnostic engine.

Return JSON:
{
  "analysis": "",
  "facts": [],
  "category": "hardware|software|network|unknown",
  "confidence": 0.0
}
"""

FIXER = """
You are a repair specialist.

Return JSON:
{
  "fixes": []
}
"""

CLARIFIER = """
You are a troubleshooting interviewer.

Return JSON:
{
  "questions": []
}
"""


def call(system, user):
    res = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user}
        ],
        response_format={"type": "json_object"}
    )
    return json.loads(res.choices[0].message.content)


def run_pipeline(text):
    diagnosis = call(DIAGNOSER, text)
    fixes = call(FIXER, json.dumps(diagnosis))

    confidence = diagnosis.get("confidence", 0.5)

    questions = []
    if confidence < 0.65:
        questions = call(CLARIFIER, json.dumps(diagnosis)).get("questions", [])

    return {
        "analysis": diagnosis.get("analysis", ""),
        "facts": diagnosis.get("facts", []),
        "category": diagnosis.get("category", "unknown"),
        "fixes": fixes.get("fixes", []),
        "questions": questions,
        "confidence": confidence
    }
