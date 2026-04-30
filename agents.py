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


# 🔥 FIND MATCHING GUIDED FLOW
def find_guided_flow(text, kb):
    text = text.lower()

    for item in kb:
        if item.get("type") == "guided":
            for t in item.get("triggers", []):
                if t in text:
                    return item

    return None


# 🔥 START GUIDED SESSION
def start_guided(flow):
    return {
        "mode": "guided",
        "flow": flow["name"],
        "step": 0,
        "question": flow["steps"][0]["question"]
    }


# 🔥 PROCESS ANSWER
def next_step(flow, step_index, answer):
    steps = flow["steps"]
    step = steps[step_index]

    key = "yes" if answer else "no"
    result = step.get(key)

    if isinstance(result, int):
        next_step_data = steps[result]
        return {
            "done": False,
            "step": result,
            "question": next_step_data["question"]
        }

    return {
        "done": True,
        "result": result
    }


def run_agent(user_input, memory):
    kb = load_kb()

    # 🔥 CONTINUE GUIDED
    if memory.get("mode") == "guided":
        flow = next((f for f in kb if f.get("name") == memory["flow"]), None)

        if not flow:
            return {"analysis": "Flow lost", "fixes": []}

        answer = user_input.lower() in ["yes", "y"]

        step_result = next_step(flow, memory["step"], answer)

        if step_result["done"]:
            return {
                "analysis": f"Diagnosis: {step_result['result']}",
                "fixes": []
            }

        memory["step"] = step_result["step"]

        return {
            "analysis": step_result["question"],
            "fixes": []
        }

    # 🔥 START GUIDED IF MATCH
    flow = find_guided_flow(user_input, kb)

    if flow:
        session = start_guided(flow)

        memory.update(session)

        return {
            "analysis": session["question"],
            "fixes": []
        }

    # 🔥 FALLBACK (no guided match)
    return {
        "analysis": "No guided flow matched. Provide more detail.",
        "fixes": []
    }
