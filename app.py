from flask import Flask, render_template, request, jsonify, session
import uuid

from db import init_db, load_case, save_case
from agents import run_agent
from tools import run_tool

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

    # 🧠 AI + KB
    result = run_agent(user_input, case)

    # 🛠 Tool execution
    tool_result = None
    if result.get("tool", {}).get("name"):
        tool_result = run_tool(
            result["tool"]["name"],
            result["tool"].get("input", {})
        )
        case["tools"].append(tool_result)

    # 💾 Save case
    case["history"].append(result)
    case["facts"].extend(result.get("facts", []))
    case["fixes"].extend(result.get("fixes", []))
    case["confidence"] = result.get("confidence", case["confidence"])

    save_case(cid, case)

    return jsonify({
        "result": result,
        "tool_result": tool_result
    })


@app.route("/api/case")
def get_case():
    return jsonify(load_case(get_cid()))


if __name__ == "__main__":
    app.run(debug=True)
