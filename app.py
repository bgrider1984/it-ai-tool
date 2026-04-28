from flask import Flask, render_template, request, jsonify, session
import uuid

from agents import run_pipeline
from db import init_db, load_case, save_case

app = Flask(__name__)
app.secret_key = "change-this"

init_db()


def get_case_id():
    if "cid" not in session:
        session["cid"] = str(uuid.uuid4())
    return session["cid"]


def update_case(case_id, result):
    case = load_case(case_id)

    case["history"].append(result)
    case["facts"].extend(result["facts"])
    case["fixes"].extend(result["fixes"])
    case["questions"].extend(result["questions"])
    case["confidence"] = result["confidence"]

    save_case(case_id, case)

    return case


@app.route("/")
def home():
    return render_template("dashboard.html")


@app.route("/api/analyze", methods=["POST"])
def analyze():
    case_id = get_case_id()
    text = request.json.get("text", "")

    result = run_pipeline(text)

    updated = update_case(case_id, result)

    return jsonify(result)


@app.route("/api/case")
def case():
    case_id = get_case_id()
    return jsonify(load_case(case_id))


if __name__ == "__main__":
    app.run(debug=True)
