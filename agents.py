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


# 🔍 Find guided flow
def find_guided_flow(text, kb):
    text = text.lower()

    for item in kb:
        if item.get("type") == "guided":
            for t in item.get("triggers", []):
                if t in text:
                    return item
    return None


# 🔍 Find result mapping
def find_result(name, kb):
    for item in kb:
        if item.get("type") == "result" and item.get("name") == name:
            return item
    return None


def start_guided(flow):
    return {
        "mode": "guided",
        "flow": flow["name"],
        "step": 0,
        "analysis": flow["steps"][0]["question"],
        "fixes": []
    }


def next_step(flow, step_index, answer):
    steps = flow["steps"]
    step = steps[step_index]

    key = "yes" if answer else "no"
    result = step.get(key)

    if isinstance(result, int):
        return {
            "done": False,
            "step": result,
            "question": steps[result]["question"]
        }

    return {
        "done": True,
        "result": result
    }


def run_agent(user_input, memory):
    kb = load_kb()

    # 🔁 CONTINUE GUIDED FLOW
    if memory.get("mode") == "guided":
        flow = next((f for f in kb if f.get("name") == memory["flow"]), None)

        if not flow:
            return {"analysis": "Flow lost", "fixes": []}

        answer = user_input.lower() in ["yes", "y"]

        step_result = next_step(flow, memory["step"], answer)

        # 🔥 FINAL RESULT → INJECT FIXES
        if step_result["done"]:
            result_name = step_result["result"]
            result_data = find_result(result_name, kb)

            if result_data:
                return {
                    "analysis": result_data.get("analysis"),
                    "fixes": result_data.get("fixes", [])
                }

            return {
                "analysis": f"Diagnosis: {result_name}",
                "fixes": []
            }

        # 🔁 CONTINUE FLOW
        memory["step"] = step_result["step"]

        return {
            "analysis": step_result["question"],
            "fixes": []
        }

    # 🚀 START NEW GUIDED FLOW
    flow = find_guided_flow(user_input, kb)

    if flow:
        session = start_guided(flow)
        memory.update(session)

        return {
            "analysis": session["analysis"],
            "fixes": []
        }

    # 🧠 FALLBACK
    return {
        "analysis": "No guided troubleshooting available for this issue yet.",
        "fixes": []
    }
