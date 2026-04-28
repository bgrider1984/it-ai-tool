# Simple in-memory case store (upgradeable to DB later)

CASES = {}

def get_case(session_id):
    if session_id not in CASES:
        CASES[session_id] = {
            "history": [],
            "facts": [],
            "fixes": [],
            "questions": [],
            "confidence": 0.0
        }
    return CASES[session_id]


def update_case(session_id, data):
    case = get_case(session_id)

    case["history"].append(data)

    case["facts"].extend(data.get("facts", []))
    case["fixes"].extend(data.get("fixes", []))
    case["questions"].extend(data.get("questions", []))

    case["confidence"] = data.get("confidence", case["confidence"])

    return case
