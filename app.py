from flask import Flask, render_template, request, jsonify, session
import uuid

from agents import analyze_issue
from memory import get_case, update_case

app = Flask(__name__)
app.secret_key = "dev-key-change-this"


# ----------------------------
# SESSION ID
# ----------------------------
def get_session_id():
    if "sid" not in session:
        session["sid"] = str(uuid.uuid4())
    return session["sid"]


# ----------------------------
# UI
# ----------------------------
@app.route("/")
def dashboard():
    return render_template("dashboard.html")


# ----------------------------
# AI PIPELINE
# ----------------------------
@app.route("/api/analyze", methods=["POST"])
def analyze():
    text = request.json.get("text", "")
    sid = get_session_id()

    case = get_case(sid)

    result = analyze_issue(text, case)

    update_case(sid, result)

    return jsonify(result)


# ----------------------------
# GET MEMORY (debug view)
# ----------------------------
@app.route("/api/memory")
def memory():
    sid = get_session_id()
    return jsonify(get_case(sid))


if __name__ == "__main__":
    app.run(debug=True)
