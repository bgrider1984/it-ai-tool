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
            "last_response": "",
            "last_q": None
        }

    return session["sid"]

# ----------------------------
# HELPERS
# ----------------------------
def is_yes(msg):
    return any(x in msg for x in ["yes", "y", "yeah", "yep", "fixed", "working", "resolved"])

def is_no(msg):
    return any(x in msg for x in ["no", "n", "nope", "still"])

def interpret_answer(msg, state):
    """
    Returns:
    - "resolved"
    - "not_resolved"
    - None
    """
    if state["last_q"] == "fixed":
        if is_yes(msg):
            return "resolved"
        if is_no(msg):
            return "not_resolved"

    if state["last_q"] == "still":
        if is_yes(msg):  # YES = still broken
            return "not_resolved"
        if is_no(msg):   # NO = no longer happening
            return "resolved"

    return None

def safe_response(state, text):
    if state["last_response"] == text:
        return text + "\n\nLet’s continue."
    state["last_response"] = text
    return text

# ----------------------------
# FLOW DETECT
# ----------------------------
def detect_flow(msg):
    if "keyboard" in msg:
        return "keyboard"
    return "keyboard"

# ----------------------------
# STEPS
# ----------------------------
def step1(state):
    state["last_q"] = "fixed"
    return (
        "Step 1: Check keyboard power\n\n"
        "• Replace batteries\n"
        "• Make sure it is ON\n\n"
        "Did that fix the issue?"
    )

def step2(state):
    state["last_q"] = "still"
    return (
        "Step 2: Check signal interference\n\n"
        "• Move keyboard closer\n"
        "• Remove nearby wireless devices\n\n"
        "Is the issue still happening?"
    )

def step3(state):
    state["last_q"] = "fixed"
    return (
        "Step 3: Try a different USB port\n\n"
        "• Plug receiver into another port\n\n"
        "Did that fix the issue?"
    )

def step4(state):
    state["last_q"] = "fixed"
    return (
        "Step 4: Update keyboard driver\n\n"
        "• Right-click Start → Device Manager\n"
        "• Expand 'Keyboards'\n"
        "• Update driver\n\n"
        "Restart PC after\n\n"
        "Did that fix the issue?"
    )

def step5(state):
    state["last_q"] = None
    return (
        "Step 5: Hardware test\n\n"
        "• Plug keyboard into another computer\n\n"
        "Tell me what happens."
    )

def step6(state):
    state["last_q"] = "fixed"
    return (
        "Final Step: Reinstall driver\n\n"
        "• Device Manager → Uninstall keyboard\n"
        "• Restart PC\n\n"
        "Did that fix the issue?"
    )

# ----------------------------
# MAIN ENGINE
# ----------------------------
@app.route("/ask", methods=["POST"])
def ask():

    msg = (request.json.get("message") or "").lower()

    sid = get_sid()
    state = sessions[sid]

    if state["flow"] is None:
        state["flow"] = detect_flow(msg)

    answer = interpret_answer(msg, state)

    # ============================
    # KEYBOARD FLOW
    # ============================
    if state["flow"] == "keyboard":

        if state["step"] == 0:
            state["step"] = 1
            return jsonify({"response": safe_response(state, step1(state))})

        if state["step"] == 1:
            if answer == "resolved":
                return jsonify({"response": "Perfect — glad that fixed it 👍"})
            state["step"] = 2
            return jsonify({"response": safe_response(state, step2(state))})

        if state["step"] == 2:
            if answer == "not_resolved":
                state["step"] = 3
                return jsonify({"response": safe_response(state, step3(state))})
            return jsonify({"response": "Good — interference was the issue."})

        if state["step"] == 3:
            if answer == "resolved":
                return jsonify({"response": "Great — issue fixed."})
            state["step"] = 4
            return jsonify({"response": safe_response(state, step4(state))})

        if state["step"] == 4:
            if answer == "resolved":
                return jsonify({"response": "Driver update fixed it 👍"})
            state["step"] = 5
            return jsonify({"response": safe_response(state, step5(state))})

        if state["step"] == 5:
            if "works fine" in msg:
                state["step"] = 6
                return jsonify({"response": safe_response(state, step6(state))})

            if "still" in msg:
                return jsonify({"response": "That confirms the keyboard is faulty. Replace it."})

            return jsonify({"response": "What happened when you tested it on another computer?"})

        if state["step"] == 6:
            if answer == "resolved":
                return jsonify({"response": "Perfect — issue resolved 👍"})
            return jsonify({"response": "This may require deeper system troubleshooting."})

    return jsonify({"response": "Tell me more."})

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

@app.route("/health")
def health():
    return jsonify({"status": "ok"})

# ----------------------------
# RUN
# ----------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
