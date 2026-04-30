from flask import Flask, render_template, request, jsonify, session
import uuid

from db import init_db, load_case, save_case
from agents import run_agent
from tools import run_fix, verify_fix
from monitor import get_system_metrics, detect_alerts

app = Flask(__name__)
app.secret_key = "safe-key"

init_db()


def get_cid():
    if "cid" not in session:
        session["cid"] = str(uuid.uuid4())
    return session["cid"]


def safe_response(data=None, error=None):
    return jsonify({
        "success": error is None,
        "data": data or {},
        "error": error
    })


@app.route("/")
def home():
    try:
        return render_template("dashboard.html")
    except Exception as e:
        return f"Template error: {str(e)}"


@app.route("/api/run", methods=["POST"])
def run():
    try:
        cid = get_cid()
        case = load_case(cid)

        text = request.json.get("text", "")

        result = run_agent(text, case)

        # 🔥 Save guided + normal flow history
        case["history"].append({
            "type": "step",
            "input": text,
            "response": result.get("analysis")
        })

        save_case(cid, case)

        return safe_response(result)

    except Exception as e:
        return safe_response(error=str(e))


@app.route("/api/fix", methods=["POST"])
def fix():
    try:
        cid = get_cid()
        case = load_case(cid)

        fix_id = request.json.get("fix")
        result = run_fix(fix_id)

        case["history"].append({
            "type": "fix",
            "fix": fix_id,
            "output": result
        })

        save_case(cid, case)

        return safe_response(result)

    except Exception as e:
        return safe_response(error=str(e))


@app.route("/api/verify", methods=["POST"])
def verify():
    try:
        cid = get_cid()
        case = load_case(cid)

        fix_id = request.json.get("fix")
        result = verify_fix(fix_id)

        case["history"].append({
            "type": "verify",
            "fix": fix_id,
            "result": result
        })

        save_case(cid, case)

        return safe_response(result)

    except Exception as e:
        return safe_response(error=str(e))


@app.route("/api/monitor")
def monitor():
    try:
        metrics = get_system_metrics()
        alerts = detect_alerts(metrics)

        return safe_response({
            "metrics": metrics,
            "alerts": alerts
        })

    except Exception as e:
        return safe_response(error=str(e))


@app.route("/api/case")
def case():
    try:
        return safe_response(load_case(get_cid()))
    except Exception as e:
        return safe_response(error=str(e))


if __name__ == "__main__":
    app.run(debug=True)
