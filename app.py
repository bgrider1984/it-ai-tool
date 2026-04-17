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
            "history": []
        }

    return session["sid"]

# ----------------------------
# STEP CONTENT
# ----------------------------
def restart_step():
    return (
        "Step 1: Restart your computer\n\n"
        "• Click Start → Power → Restart\n"
        "• Do NOT shut down\n\n"
        "After restart:\n"
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
        "Step 3: Identify high memory usage\n\n"
        "In Task Manager:\n"
        "• Go to Processes tab\n"
        "• Click 'Memory' column to sort\n\n"
        "Look for:\n"
        "• Apps using the most memory\n\n"
        "Then:\n"
        "• Right-click → End Task (ONLY if safe)\n\n"
        "Tell me which process is using the most memory."
    )

def safe_process_explanation():
    return (
        "How to know if a process is safe to close:\n\n"

        "Generally SAFE to close:\n"
        "• Web browsers (Chrome, Edge)\n"
        "• Apps you opened (Discord, Steam, etc.)\n\n"

        "DO NOT close:\n"
        "• Anything named 'System'\n"
        "• 'Windows Explorer'\n"
        "• 'Service Host'\n"
        "• 'svchost.exe'\n\n"

        "Tip:\n"
        "If you're unsure, tell me the process name and I’ll check it for you."
    )

def explorer_fix_step():
    return (
        "Step 4: Fix missing desktop icons\n\n"
        "In Task Manager:\n"
        "• Find 'Windows Explorer'\n"
        "• Right-click → Restart\n\n"
        "This reloads your desktop.\n\n"
        "Did your icons come back?"
    )

# ----------------------------
# DETECTION
# ----------------------------
def detect(msg):
    t = msg.lower()

    return {
        "high_memory": "memory" in t and any(x in t for x in ["90", "95", "100"]),
        "icons_missing": "icons disappeared" in t or "desktop disappeared" in t,
        "asking_safe": "safe" in t,
        "asking_process": "process" in t
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
# MAIN ENGINE
# ----------------------------
@app.route("/ask", methods=["POST"])
def ask():

    data = request.json or {}
    msg = data.get("message", "")

    sid = get_sid()
    state = sessions[sid]

    signals = detect(msg)

    # ----------------------------
    # STEP 0
    # ----------------------------
    if state["step"] == 0:
        state["step"] = 1
        return jsonify({"response": restart_step()})

    # ----------------------------
    # STEP 1 (RESTART RESULT)
    # ----------------------------
    if state["step"] == 1:
        if "no" in msg.lower():
            state["step"] = 2
            return jsonify({"response": task_manager_step()})
        return jsonify({"response": "Good — issue resolved."})

    # ----------------------------
    # STEP 2 (TASK MANAGER)
    # ----------------------------
    if state["step"] == 2:

        if signals["high_memory"]:
            state["step"] = 3
            return jsonify({"response": memory_fix_step()})

        return jsonify({"response": "Please provide CPU and Memory usage."})

    # ----------------------------
    # STEP 3 (MEMORY FIX)
    # ----------------------------
    if state["step"] == 3:

        if signals["asking_safe"]:
            return jsonify({"response": safe_process_explanation()})

        if signals["icons_missing"]:
            state["step"] = 4
            return jsonify({"response": explorer_fix_step()})

        return jsonify({
            "response": "Tell me the name of the process using the most memory."
        })

    # ----------------------------
    # STEP 4 (EXPLORER FIX)
    # ----------------------------
    if state["step"] == 4:

        if "yes" in msg.lower():
            return jsonify({"response": "Good — desktop restored. Try opening apps again."})

        return jsonify({"response": "Let’s continue. Are apps opening now?"})

    # ----------------------------
    # FINAL SAFETY
    # ----------------------------
    return jsonify({
        "response": "Continue and I’ll guide the next step."
    })

# ----------------------------
# HEALTH
# ----------------------------
@app.route("/health")
def health():
    return jsonify({"status": "ok"})

# ----------------------------
# RUN
# ----------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
