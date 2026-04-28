from openai import OpenAI
import os
import json

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

MODEL = "gpt-4o-mini"


# ----------------------------
# SYSTEM PROMPTS (AGENTS)
# ----------------------------

DIAGNOSTIC_AGENT = """
You are a Diagnostic AI Agent.

Your job:
- Identify root cause of technical issues
- Extract observable facts
- Determine likely category: hardware, software, network, unknown

Return JSON ONLY:
{
  "analysis": "",
  "facts": [],
  "category": "",
  "confidence": 0.0
}
"""

FIX_AGENT = """
You are a Repair AI Agent.

Your job:
- Generate step-by-step fixes based on diagnosis
- Keep steps actionable and simple

Return JSON ONLY:
{
  "fixes": []
}
"""

CLARIFIER_AGENT = """
You are a Clarification AI Agent.

If confidence is below 0.6, generate follow-up questions.

Return JSON ONLY:
{
  "questions": []
}
"""


# ----------------------------
# AGENT CALL FUNCTION
# ----------------------------

def run_agent(prompt, system):
    res = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": prompt}
        ],
        response_format={"type": "json_object"}
    )

    return json.loads(res.choices[0].message.content)


# ----------------------------
# FULL PIPELINE
# ----------------------------

def analyze_issue(text, memory):
    
    # 1. Diagnose
    diagnosis = run_agent(text, DIAGNOSTIC_AGENT)

    # 2. Fix generation
    fixes = run_agent(
        json.dumps(diagnosis),
        FIX_AGENT
    )

    confidence = diagnosis.get("confidence", 0.5)

    # 3. Clarifying questions if needed
    questions = []
    if confidence < 0.6:
        questions = run_agent(
            json.dumps(diagnosis),
            CLARIFIER_AGENT
        ).get("questions", [])

    return {
        "analysis": diagnosis.get("analysis", ""),
        "facts": diagnosis.get("facts", []),
        "category": diagnosis.get("category", "unknown"),
        "fixes": fixes.get("fixes", []),
        "questions": questions,
        "confidence": confidence
    }
