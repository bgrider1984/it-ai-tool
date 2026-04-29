from flask import Flask, render_template, request, jsonify, session
import uuid

from db import init_db, load_case, save_case
from agents import run_agent
from tools import run_fix, verify_fix
from monitor import get_system_metrics, detect_alerts

app = Flask(__name__)
app.secret_key = "secret"

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

    text = request.json.get("text", "")

    result = run_agent(text, case)

    case["history"].append({
        "type": "analysis",
        "input": text,
        "analysis": result["analysis"]
    })

    case["fixes"] = result["fixes"]

    save_case(cid, case)

    return jsonify(result)


@app.route("/api/fix", methods=["POST"])
def fix():
    cid = get_cid()
    case = load_case(cid)

    fix_id = request.json.get("fix")

    result = run_fix(fix_id)

    case["history"].append({
        "type": "fix",
        "fix": fix_id,
        "output": result.get("output")
    })

    save_case(cid, case)

    return jsonify(result)


@app.route("/api/verify", methods=["POST"])
def verify():
    cid = get_cid()
    case = load_case(cid)

    fix_id = request.json.get("fix")

    result = verify_fix(fix_id)

    case["history"].append({
        "type": "verify",
        "fix": fix_id,
        "result": result.get("verification")
    })

    save_case(cid, case)

    return jsonify(result)


@app.route("/api/monitor")
def monitor():
    return jsonify({
        "metrics": get_system_metrics(),
        "alerts": detect_alerts(get_system_metrics())
    })


@app.route("/api/case")
def case():
    return jsonify(load_case(get_cid()))


if __name__ == "__main__":
    app.run(debug=True)
