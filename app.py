import os
import uuid
from flask import Flask, request, jsonify, session, redirect, render_template

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "dev-secret")

# ----------------------------
# SESSION STORAGE
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
            "history": [],
            "restart_done": False
        }

    return session["sid"]

# ----------------------------
# SLOT PARSER
# ----------------------------
def update_slots(msg, state):
    t = msg.lower()

    if "all" in t:
        state["slots"]["scope"] = "all"
    elif "one" in t:
        state["slots"]["scope"] = "one"

    if "update" in t:
        state["slots"]["trigger"] = "update"
    elif "restart" in t:
        state["slots"]["trigger"] = "restart"

    if "error" in t:
        state["slots"]["error"] = "yes"
    elif "none" in t:
        state["slots"]["error"] = "no"

    state["history"].append(msg.lower())

    missing = [k for k, v in state["slots"].items() if v is None]
    return state, missing

# ----------------------------
# STOPLIGHT DIAGNOSTICS
# ----------------------------
def stoplight(slots):

    results = []

    # SYSTEM WIDE + UPDATE
    if slots["scope"] == "all" and slots["trigger"] == "update":
        results.append(("🟢", "Windows update caused system shell issue"))
        results.append(("🟡", "User profile corruption"))
        results.append(("🔴", "Hardware failure"))

    # SYSTEM WIDE ONLY
    elif slots["scope"] == "all":
        results.append(("🟢", "Startup/service issue"))
        results.append(("🟡", "User profile corruption"))
        results.append(("🔴", "Disk failure"))

    # SINGLE APP
    elif slots["scope"] == "one":
        results.append(("🟢", "App corruption or install issue"))
        results.append(("🟡", "Permissions issue"))
        results.append(("🔴", "OS-level corruption"))

    else:
        results.append(("🟢", "Need more info to classify issue"))

    return results

# ----------------------------
# ROOT FIX ENGINE (KEEP IT SIMPLE FIRST)
# ----------------------------
def simple_fix(state):

    if not state.get("restart_done"):
        state["restart_done"] = True

        return (
            "Step 1 (K.I.S.S.):\n"
            "👉 Restart your computer completely\n"
            "Then try opening your apps again.\n\n"
            "Tell me: Did that fix it?"
        )

    return "Now let's continue troubleshooting based on results."

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
# MAIN ENGINE
# ----------------------------
@app.route("/ask", methods=["POST"])
def ask():

    data = request.json or {}
    msg = data.get("message", "")

    sid = get_sid()
    state = sessions[sid]

    state, missing = update_slots(msg, state)

    # ----------------------------
    # STEP 1: ALWAYS START SIMPLE
    # ----------------------------
    if state["step"] == 0:
        state["step"] = 1
        return jsonify({
            "response": simple_fix(state)
        })

    # ----------------------------
    # STEP 2: IF USER CONFIRMS ISSUE STILL EXISTS
    # ----------------------------
    if state["step"] == 1:

        if "yes" in msg.lower() or "still" in msg.lower():
            state["step"] = 2

            lights = stoplight(state["slots"])

            formatted = "\n".join([f"{c} {t}" for c, t in lights])

            return jsonify({
                "response":
                    "Okay, let's go deeper.\n\n"
                    "Possible causes:\n" + formatted + "\n\n"
                    "Tell me what changed recently or what you observed."
            })

        return jsonify({
            "response": "Great — seems like the restart may have helped. Let me know if it happens again."
        })

    # ----------------------------
    # STEP 3: FINAL DIAGNOSIS
    # ----------------------------
    lights = stoplight(state["slots"])

    formatted = "\n".join([f"{c} {t}" for c, t in lights])

    return jsonify({
        "response":
            "Final Diagnostic Overview:\n\n" +
            formatted +
            "\n\nNext step: describe what you see when trying to open the apps."
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
