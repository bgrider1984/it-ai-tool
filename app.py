from flask import Flask, render_template, request, jsonify, session
import uuid

from db import init_db, load_case, save_case
from agents import run_agent
from tools import run_tool, run_fix, verify_fix
from monitor import get_system_metrics, detect_alerts

app = Flask(__name__)
app.secret_key = "change-this"

init_db()


def get_cid():
    if "cid" not in session:
        session["cid"] = str(uuid.uuid4())
    return session["cid"]


@app.route("/")
def home():
    return render_template("dashboard.html")


@app.route("/api/run", methods=["POST"])
def run():
    cid = get_cid()
    case = load_case(cid)

    user_input = request.json.get("text", "")

    result = run_agent(user_input, case)

    tool_result = None
    if result.get("tool", {}).get("name"):
        tool_result = run_tool(result["tool"]["name"])

    case["history"].append({
        "type": "analysis",
        "input": user_input,
        "analysis": result.get("analysis")
    })

    case["fixes"] = result.get("fixes", [])

    save_case(cid, case)

    return jsonify({
        "result": result,
        "tool_result": tool_result
    })


# 🔧 RUN FIX
@app.route("/api/fix", methods=["POST"])
def fix():
    cid = get_cid()
    case = load_case(cid)

    fix_name = request.json.get("fix")

    result = run_fix(fix_name)

    case["history"].append({
        "type": "fix",
        "fix": fix_name,
        "output": result.get("output")
    })

    save_case(cid, case)

    return jsonify(result)


# 🔍 VERIFY FIX
@app.route("/api/verify", methods=["POST"])
def verify():
    cid = get_cid()
    case = load_case(cid)

    fix_name = request.json.get("fix")

    result = verify_fix(fix_name)

    case["history"].append({
        "type": "verify",
        "fix": fix_name,
        "result": result.get("verification")
    })

    save_case(cid, case)

    return jsonify(result)


@app.route("/api/monitor")
def monitor():
    metrics = get_system_metrics()
    alerts = detect_alerts(metrics)
    return jsonify({"metrics": metrics, "alerts": alerts})


@app.route("/api/case")
def case():
    return jsonify(load_case(get_cid()))


if __name__ == "__main__":
    app.run(debug=True)
