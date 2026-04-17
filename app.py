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
            "flow": None,
            "history": [],
            "answered_cpu": False
        }

    return session["sid"]

# ----------------------------
# DETECT ISSUE TYPE
# ----------------------------
def detect_flow(msg):
    t = msg.lower()

    if "keyboard" in t:
        return "keyboard"

    if "app" in t:
        return "apps"

    return "general"

# ----------------------------
# KEYBOARD FLOW
# ----------------------------
def keyboard_step_1():
    return (
        "Step 1: Check keyboard power\n\n"
        "If this is a wireless keyboard:\n"
        "• Replace the batteries with new ones\n"
        "• Make sure the keyboard is turned ON\n\n"
        "If it uses a USB receiver:\n"
        "• Unplug it and plug it back in\n\n"
        "Tell me: Did that fix the issue?"
    )

def keyboard_step_2():
    return (
        "Step 2: Check signal interference\n\n"
        "• Move the keyboard closer to the computer\n"
        "• Remove nearby wireless devices temporarily\n\n"
        "Tell me if the issue still happens."
    )

def keyboard_step_3():
    return (
        "Step 3: Check USB receiver / drivers\n\n"
        "• Try a different USB port\n"
        "• Restart computer\n\n"
        "If issue continues, we may check drivers next."
    )

# ----------------------------
# APP FLOW
# ----------------------------
def restart_step():
    return (
        "Step 1: Restart your computer\n\n"
        "• Click Start → Power → Restart\n\n"
        "After restart:\n"
        "• Try opening apps again\n\n"
        "Did that fix the issue?"
    )

def task_manager_step():
    return (
        "Step 2: Check system usage\n\n"
        "Open Task Manager:\n"
        "• Press Ctrl + Shift + Esc\n\n"
        "Look at:\n"
        "• CPU %\n"
        "• Memory %\n\n"
        "What numbers do you see?"
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

    state["history"].append(msg.lower())

    # ----------------------------
    # DETECT FLOW ON FIRST MESSAGE
    # ----------------------------
    if state["flow"] is None:
        state["flow"] = detect_flow(msg)

    flow = state["flow"]

    # ============================
    # KEYBOARD FLOW
    # ============================
    if flow == "keyboard":

        if state["step"] == 0:
            state["step"] = 1
            return jsonify({"response": keyboard_step_1()})

        if state["step"] == 1:
            if "yes" in msg.lower():
                return jsonify({"response": "Great — issue resolved."})

            state["step"] = 2
            return jsonify({"response": keyboard_step_2()})

        if state["step"] == 2:
            state["step"] = 3
            return jsonify({"response": keyboard_step_3()})

        return jsonify({"response": "If the issue continues, we may need to check drivers or hardware."})

    # ============================
    # APP FLOW
    # ============================
    if flow == "apps":

        # STEP 0
        if state["step"] == 0:
            state["step"] = 1
            return jsonify({"response": restart_step()})

        # STEP 1
        if state["step"] == 1:
            if "no" in msg.lower():
                state["step"] = 2
                return jsonify({"response": task_manager_step()})

            return jsonify({"response": "Great — issue resolved."})

        # STEP 2
        if state["step"] == 2:

            if "%" in msg:
                state["answered_cpu"] = True
                return jsonify({"response": "Thanks — system usage looks normal. Let’s check startup or app issues next."})

            if not state["answered_cpu"]:
                return jsonify({"response": "Just to confirm — what % do you see for CPU and memory?"})

    # ============================
    # FALLBACK
    # ============================
    return jsonify({
        "response": "Tell me more about the issue and I’ll guide you."
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
