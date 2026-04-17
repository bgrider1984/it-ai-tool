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
            "last_question": None
        }

    return session["sid"]

# ----------------------------
# FLOW DETECTION
# ----------------------------
def detect_flow(msg):
    t = msg.lower()

    if "keyboard" in t:
        return "keyboard"
    if "crash" in t:
        return "crash"
    if "app" in t:
        return "apps"

    return None

# ----------------------------
# NEW ISSUE DETECTION
# ----------------------------
def is_new_issue(msg, state):
    detected = detect_flow(msg)

    if detected and detected != state["flow"]:
        return detected

    return None

# ----------------------------
# KEYBOARD STEPS
# ----------------------------
def step1():
    return (
        "Step 1: Check keyboard power\n\n"
        "• Replace batteries\n"
        "• Make sure it is ON\n\n"
        "Did that fix the issue?"
    )

def step2():
    return (
        "Step 2: Check signal interference\n\n"
        "• Move keyboard closer\n"
        "• Remove wireless interference\n\n"
        "Is the issue still happening?"
    )

def step3():
    return (
        "Step 3: Try a different USB port\n\n"
        "• Plug receiver into another port\n\n"
        "Did that fix the issue?"
    )

def step4():
    return (
        "Step 4: Update keyboard driver\n\n"
        "• Right-click Start → Device Manager\n"
        "• Expand Keyboards\n"
        "• Right-click → Update driver\n\n"
        "Did that fix the issue?"
    )

# ----------------------------
# CRASH FLOW
# ----------------------------
def crash_start():
    return (
        "It looks like a system crash issue.\n\n"
        "Step 1:\n"
        "• Restart the computer\n\n"
        "Let me know if it crashes again."
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
    msg = data.get("message", "").lower()

    sid = get_sid()
    state = sessions[sid]

    # ----------------------------
    # NEW ISSUE HANDLING
    # ----------------------------
    new_issue = is_new_issue(msg, state)
    if new_issue:
        state["flow"] = new_issue
        state["step"] = 0

    # ----------------------------
    # INITIAL FLOW SET
    # ----------------------------
    if state["flow"] is None:
        state["flow"] = detect_flow(msg) or "keyboard"

    flow = state["flow"]

    # ============================
    # KEYBOARD FLOW
    # ============================
    if flow == "keyboard":

        if state["step"] == 0:
            state["step"] = 1
            state["last_question"] = "fixed"
            return jsonify({"response": step1()})

        if state["step"] == 1:
            if "yes" in msg:
                return jsonify({"response": "Great — issue resolved."})
            state["step"] = 2
            state["last_question"] = "still"
            return jsonify({"response": step2()})

        if state["step"] == 2:
            if "yes" in msg:  # YES = still broken
                state["step"] = 3
                state["last_question"] = "fixed"
                return jsonify({"response": step3()})
            else:
                return jsonify({"response": "Good — interference was the issue."})

        if state["step"] == 3:
            if "yes" in msg:
                return jsonify({"response": "Great — issue resolved."})
            state["step"] = 4
            state["last_question"] = "fixed"
            return jsonify({"response": step4()})

        if state["step"] == 4:
            if "yes" in msg:
                return jsonify({"response": "Driver update fixed the issue."})
            return jsonify({"response": "Next step would be hardware testing."})

    # ============================
    # CRASH FLOW
    # ============================
    if flow == "crash":

        if state["step"] == 0:
            state["step"] = 1
            return jsonify({"response": crash_start()})

        return jsonify({"response": "Tell me what happens after restart."})

    # ============================
    # FALLBACK
    # ============================
    return jsonify({
        "response": "Tell me more about the issue."
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
