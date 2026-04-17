import os
import uuid
from flask import Flask, request, jsonify, session, redirect, render_template

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "dev-secret")

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

    state["history"].append(t)
    return state

# ----------------------------
# DETECTION ENGINE
# ----------------------------
def detect_conditions(msg):
    t = msg.lower()

    return {
        "high_memory": "memory" in t and any(x in t for x in ["90", "95", "100"]),
        "high_cpu": "cpu" in t and any(x in t for x in ["90", "95", "100"]),
        "desktop_missing": "icons disappeared" in t or "desktop disappeared" in t
    }

# ----------------------------
# STEP BUILDERS
# ----------------------------
def restart_step():
    return (
        "Step 1: Restart your computer\n\n"
        "What to do:\n"
        "• Click Start → Power → Restart\n\n"
        "Important:\n"
        "• Use Restart, not Shutdown\n\n"
        "After reboot:\n"
        "• Try opening apps again\n\n"
        "Did that fix the issue?"
    )

def task_manager_step():
    return (
        "Step 2: Check system usage\n\n"
        "Open Task Manager:\n"
        "• Press Ctrl + Shift + Esc\n\n"
        "Check:\n"
        "• CPU usage\n"
        "• Memory usage\n\n"
        "Reply with what you see."
    )

def memory_fix_step():
    return (
        "High memory usage detected.\n\n"
        "Step 3: Identify heavy processes\n\n"
        "In Task Manager:\n"
        "• Click 'Processes'\n"
        "• Sort by Memory (click column header)\n\n"
        "Look for:\n"
        "• Anything using a large % of memory\n\n"
        "Then:\n"
        "• Right-click → End Task (only if safe, avoid system processes)\n\n"
        "After that:\n"
        "• Try opening apps again\n\n"
        "Tell me what process was using the most memory."
    )

def explorer_fix_step():
    return (
        "Desktop icons missing usually means Windows Explorer crashed.\n\n"
        "Step 4: Restart Windows Explorer\n\n"
        "In Task Manager:\n"
        "• Scroll down to 'Windows Explorer'\n"
        "• Right-click it\n"
        "• Click 'Restart'\n\n"
        "What this does:\n"
        "• Reloads desktop and taskbar\n\n"
        "Tell me if your icons come back."
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

    update_slots(msg, state)
    signals = detect_conditions(msg)

    # ----------------------------
    # HANDLE HOW-TO
    # ----------------------------
    if "how do i" in msg.lower():
        return jsonify({"response": task_manager_step()})

    # ----------------------------
    # STEP 0
    # ----------------------------
    if state["step"] == 0:
        state["step"] = 1
        return jsonify({"response": restart_step()})

    # ----------------------------
    # STEP 1
    # ----------------------------
    if state["step"] == 1:
        if "no" in msg.lower() or "still" in msg.lower():
            state["step"] = 2
            return jsonify({"response": task_manager_step()})
        return jsonify({"response": "Great — sounds like the issue is resolved."})

    # ----------------------------
    # SIGNAL-DRIVEN RESPONSES
    # ----------------------------
    if signals["desktop_missing"]:
        state["step"] = 4
        return jsonify({"response": explorer_fix_step()})

    if signals["high_memory"]:
        state["step"] = 3
        return jsonify({"response": memory_fix_step()})

    # ----------------------------
    # DEFAULT PROGRESSION
    # ----------------------------
    return jsonify({
        "response": "Tell me what you are seeing now and I will guide the next step."
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
