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

    if "error" in t or "crash" in t:
        state["slots"]["error"] = "yes"
    elif "none" in t or "no error" in t:
        state["slots"]["error"] = "no"

    state["history"].append(msg.lower())

    missing = [k for k, v in state["slots"].items() if v is None]
    return state, missing

# ----------------------------
# STOPLIGHT DIAGNOSTICS
# ----------------------------
def stoplight(slots):

    results = []

    if slots["scope"] == "all" and slots["trigger"] == "update":
        results.append(("🟢", "Windows update may have affected system processes"))
        results.append(("🟡", "User profile or permissions issue"))
        results.append(("🔴", "Hardware failure"))

    elif slots["scope"] == "all":
        results.append(("🟢", "Startup or system service issue"))
        results.append(("🟡", "Profile corruption"))
        results.append(("🔴", "Disk failure"))

    elif slots["scope"] == "one":
        results.append(("🟢", "Application corruption"))
        results.append(("🟡", "Permissions issue"))
        results.append(("🔴", "Operating system issue"))

    else:
        results.append(("🟢", "More information needed"))

    return results

# ----------------------------
# DETAILED STEP ENGINE
# ----------------------------
def restart_step():
    return (
        "Step 1: Restart your computer\n\n"

        "What to do:\n"
        "• Click the Start Menu\n"
        "• Select the Power icon\n"
        "• Click 'Restart'\n\n"

        "Important:\n"
        "• Do NOT shut down — use Restart specifically\n\n"

        "What this does:\n"
        "• Clears temporary memory issues\n"
        "• Restarts all system services\n"
        "• Fixes many app launch problems\n\n"

        "After it turns back on:\n"
        "• Try opening the apps again\n\n"

        "Tell me: Did the apps open successfully after the restart?"
    )

def task_manager_step():
    return (
        "Next Step: Check system usage in Task Manager\n\n"

        "How to open it:\n"
        "• Press Ctrl + Shift + Esc\n\n"

        "What to look for:\n"
        "• CPU usage — is it near 100%?\n"
        "• Memory usage — is it near full?\n\n"

        "What it means:\n"
        "• High CPU or memory can prevent apps from opening\n\n"

        "Tell me what you see (CPU % and Memory %)."
    )

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
    # HANDLE "HOW DO I" QUESTIONS
    # ----------------------------
    if "task manager" in msg.lower():
        return jsonify({"response": task_manager_step()})

    # ----------------------------
    # STEP 0: ALWAYS START WITH RESTART
    # ----------------------------
    if state["step"] == 0:
        state["step"] = 1
        return jsonify({"response": restart_step()})

    # ----------------------------
    # STEP 1: AFTER RESTART RESULT
    # ----------------------------
    if state["step"] == 1:

        if "yes" in msg.lower() or "fixed" in msg.lower():
            return jsonify({
                "response": "Great — that confirms it was a temporary system issue. Let me know if it happens again."
            })

        if "no" in msg.lower() or "still" in msg.lower():
            state["step"] = 2

            lights = stoplight(state["slots"])
            formatted = "\n".join([f"{c} {t}" for c, t in lights])

            return jsonify({
                "response":
                    "Since the restart did not fix it, here are the most likely causes:\n\n"
                    + formatted +
                    "\n\nNext, we’ll check system resource usage."
            })

        return jsonify({
            "response": "After restarting, did the apps open or is the issue still happening?"
        })

    # ----------------------------
    # STEP 2: NEXT ACTION
    # ----------------------------
    if state["step"] == 2:
        state["step"] = 3
        return jsonify({"response": task_manager_step()})

    # ----------------------------
    # FINAL FALLBACK
    # ----------------------------
    return jsonify({
        "response": "Continue describing what you're seeing and I’ll guide you step-by-step."
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
