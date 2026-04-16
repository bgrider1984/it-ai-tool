import os
import uuid
from flask import Flask, request, jsonify, session, redirect, render_template

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "dev-secret")

# ----------------------------
# SESSION STATE STORE
# ----------------------------
sessions = {}

USERS = {"admin@local": "admin"}

# ----------------------------
# SESSION INIT
# ----------------------------
def get_sid():
    if "sid" not in session:
        sid = str(uuid.uuid4())
        session["sid"] = sid

        sessions[sid] = {
            "step": 0,
            "slots": {
                "scope": None,
                "trigger": None,
                "error": None
            },
            "history": []
        }

    return session["sid"]

# ----------------------------
# SLOT ANALYSIS
# ----------------------------
def update_slots(msg, state):
    t = msg.lower()

    # scope
    if "all" in t or "everything" in t:
        state["slots"]["scope"] = "all"
    elif "one" in t or "single" in t:
        state["slots"]["scope"] = "one"

    # trigger
    if "update" in t:
        state["slots"]["trigger"] = "update"
    elif "restart" in t:
        state["slots"]["trigger"] = "restart"

    # error
    if "error" in t or "crash" in t:
        state["slots"]["error"] = "yes"
    elif "no error" in t or "none" in t:
        state["slots"]["error"] = "no"

    state["history"].append(msg.lower())

    missing = [k for k, v in state["slots"].items() if v is None]
    return state, missing

# ----------------------------
# ROOT CAUSE ENGINE
# ----------------------------
def diagnose(slots):

    if slots["scope"] == "all" and slots["trigger"] == "update":
        return {
            "cause": "Likely Windows update affected shell or user session",
            "fixes": [
                "Restart Windows Explorer",
                "Check Windows Update history",
                "Boot into Safe Mode and test"
            ]
        }

    if slots["scope"] == "all":
        return {
            "cause": "System-wide application launch failure",
            "fixes": [
                "Check user profile integrity",
                "Run SFC /scannow",
                "Check startup policies or antivirus blocking apps"
            ]
        }

    if slots["scope"] == "one":
        return {
            "cause": "Single application launch issue",
            "fixes": [
                "Reinstall the affected application",
                "Run as administrator",
                "Clear app cache / settings"
            ]
        }

    return {
        "cause": "Unknown system state",
        "fixes": ["Gather more information before proceeding"]
    }

# ----------------------------
# ROUTES
# ----------------------------
@app.route("/")
def home():
    return render_template("index.html")

@app.route("/dashboard")
def dashboard():
    return render_template("dashboard.html")

@app.route("/login", methods=["POST"])
def login():
    data = request.json
    if USERS.get(data.get("email")) != data.get("password"):
        return jsonify({"error": "invalid login"}), 401

    session["user"] = data.get("email")
    return jsonify({"status": "ok"})

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

# ----------------------------
# MAIN DIAGNOSTIC ENGINE
# ----------------------------
@app.route("/ask", methods=["POST"])
def ask():

    data = request.json or {}
    msg = data.get("message", "")

    # ----------------------------
    # HANDLE INTERRUPT QUESTIONS
    # ----------------------------
    if "how do i" in msg.lower():
        return jsonify({
            "response": "Press Ctrl + Shift + Esc to open Task Manager.\nThen come back and tell me what you see."
        })

    sid = get_sid()
    state = sessions[sid]

    state, missing = update_slots(msg, state)

    # ----------------------------
    # IF MISSING INFO → DO NOT ADVANCE
    # ----------------------------
    if missing:

        question_map = {
            "scope": "Is this happening to ALL apps or just ONE app?",
            "trigger": "Did this start after an UPDATE or RESTART?",
            "error": "Are you seeing ANY error messages?"
        }

        return jsonify({
            "response": "I need a bit more detail:\n\n" +
                        "\n".join([question_map[m] for m in missing])
        })

    # ----------------------------
    # FULL DIAGNOSIS
    # ----------------------------
    result = diagnose(state["slots"])

    return jsonify({
        "response":
            "Root Cause:\n" + result["cause"] + "\n\n" +
            "Recommended Fixes:\n- " + "\n- ".join(result["fixes"])
    })

# ----------------------------
# HEALTH
# ----------------------------
@app.route("/health")
def health():
    return jsonify({
        "status": "ok",
        "sessions": len(sessions)
    })

# ----------------------------
# RUN
# ----------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
