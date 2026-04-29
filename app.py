from flask import Flask, render_template, request, jsonify, session
import uuid

from db import init_db, load_case, save_case
from agents import run_agent
from tools import run_tool
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
    allow_fix = request.json.get("auto_fix", False)

    result = run_agent(user_input, case)

    tool_result = None
    if result.get("tool", {}).get("name"):
        tool_result = run_tool(result["tool"]["name"])

    fix_result = None
    if allow_fix and result.get("auto_fix"):
        fix_result = run_tool(result["auto_fix"], allow_fix=True)

    # timeline log
    entry = {
        "input": user_input,
        "analysis": result.get("analysis"),
        "confidence": result.get("confidence")
    }

    case["history"].append(entry)
    case["facts"].extend(result.get("facts", []))
    case["fixes"].extend(result.get("fixes", []))
    case["confidence"] = result.get("confidence", case["confidence"])

    save_case(cid, case)

    return jsonify({
        "result": result,
        "tool_result": tool_result,
        "fix_result": fix_result
    })


@app.route("/api/monitor")
def monitor():
    metrics = get_system_metrics()
    alerts = detect_alerts(metrics)

    return jsonify({
        "metrics": metrics,
        "alerts": alerts
    })


@app.route("/api/case")
def case():
    return jsonify(load_case(get_cid()))


if __name__ == "__main__":
    app.run(debug=True)
