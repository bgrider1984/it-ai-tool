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


@app.route("/")
def home():
    return render_template("dashboard.html")


@app.route("/api/run", methods=["POST"])
def run():
    try:
        cid = get_cid()
        case = load_case(cid)

        text = request.json.get("text", "")

        result = run_agent(text, case)

        case["history"].append({
            "type": "analysis",
            "input": text,
            "analysis": result.get("analysis")
        })

        case["fixes"] = result.get("fixes", [])

        save_case(cid, case)

        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)})


@app.route("/api/fix", methods=["POST"])
def fix():
    try:
        cid = get_cid()
        case = load_case(cid)

        fix_id = request.json.get("fix")
        result = run_fix(fix_id)

        case["history"].append({"type": "fix", "fix": fix_id})
        save_case(cid, case)

        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)})


@app.route("/api/verify", methods=["POST"])
def verify():
    try:
        cid = get_cid()
        case = load_case(cid)

        fix_id = request.json.get("fix")
        result = verify_fix(fix_id)

        case["history"].append({"type": "verify", "fix": fix_id})
        save_case(cid, case)

        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)})


@app.route("/api/monitor")
def monitor():
    try:
        metrics = get_system_metrics()
        return jsonify({
            "metrics": metrics,
            "alerts": detect_alerts(metrics)
        })
    except:
        return jsonify({"metrics": {}, "alerts": []})


@app.route("/api/case")
def case():
    try:
        return jsonify(load_case(get_cid()))
    except:
        return jsonify({"history": []})


if __name__ == "__main__":
    app.run(debug=True)
