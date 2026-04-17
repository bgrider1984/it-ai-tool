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
            "last_response": ""
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
    return None

# ----------------------------
# RESPONSE GUARD
# ----------------------------
def safe_response(state, text):
    if state["last_response"] == text:
        return text + "\n\nLet’s move to the next step."
    state["last_response"] = text
    return text

# ----------------------------
# YES / RESOLVED DETECTION
# ----------------------------
def is_yes(msg):
    yes_words = ["yes", "yeah", "yep", "y", "fixed", "working", "resolved", "all good"]
    return any(word in msg for word in yes_words)

def is_no(msg):
    return any(word in msg for word in ["no", "still", "not"])

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
        "• Remove nearby wireless devices\n\n"
        "Is the issue still happening?"
    )

def step3():
    return (
        "Step 3: Try a different USB port\n\n"
        "• Plug receiver into another port (prefer back of PC)\n\n"
        "Did that fix the issue?"
    )

def step4():
    return (
        "Step 4: Update keyboard driver\n\n"
        "• Right-click Start → Device Manager\n"
        "• Expand 'Keyboards'\n"
        "• Right-click your keyboard → Update driver\n\n"
        "Then restart your computer\n\n"
        "Did that fix the issue?"
    )

def step5():
    return (
        "Step 5: Hardware test\n\n"
        "Plug the keyboard into another computer\n\n"
        "• If issue still happens → keyboard is faulty\n"
        "• If it works fine → issue is your PC\n\n"
        "Tell me what happened."
    )

def step6():
    return (
        "Final Step: System-side fix\n\n"
        "• Open Device Manager\n"
        "• Uninstall keyboard device\n"
        "• Restart computer\n\n"
        "Windows will reinstall it\n\n"
        "Did that fix the issue?"
    )

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
    # GLOBAL RESOLUTION CHECK
    # ----------------------------
    if is_yes(msg) and state["step"] != 0:
        return jsonify({
            "response": "Perfect — glad that fixed it 👍\n\nIf anything else comes up, just let me know."
        })

    # ----------------------------
    # FLOW DETECT
    # ----------------------------
    if state["flow"] is None:
        state["flow"] = detect_flow(msg) or "keyboard"

    # ============================
    # KEYBOARD FLOW
    # ============================
    if state["flow"] == "keyboard":

        if state["step"] == 0:
            state["step"] = 1
            return jsonify({"response": safe_response(state, step1())})

        if state["step"] == 1:
            if is_yes(msg):
                return jsonify({"response": "Great — issue resolved."})
            state["step"] = 2
            return jsonify({"response": safe_response(state, step2())})

        if state["step"] == 2:
            if is_yes(msg):  # still happening
                state["step"] = 3
                return jsonify({"response": safe_response(state, step3())})
            return jsonify({"response": "Good — interference was the issue."})

        if state["step"] == 3:
            if is_yes(msg):
                return jsonify({"response": "Great — issue resolved."})
            state["step"] = 4
            return jsonify({"response": safe_response(state, step4())})

        if state["step"] == 4:
            if is_yes(msg):
                return jsonify({"response": "Driver update fixed the issue."})
            state["step"] = 5
            return jsonify({"response": safe_response(state, step5())})

        if state["step"] == 5:
            if "works fine" in msg:
                state["step"] = 6
                return jsonify({"response": safe_response(state, step6())})

            if "still" in msg:
                return jsonify({
                    "response": "That confirms the keyboard is failing. Replacement recommended."
                })

            return jsonify({
                "response": safe_response(state, "What happened when you tested it?")
            })

        if state["step"] == 6:
            if is_yes(msg):
                return jsonify({"response": "Great — issue resolved."})
            return jsonify({
                "response": "At this point, it may be a deeper system issue."
            })

    # ============================
    # FALLBACK
    # ============================
    return jsonify({
        "response": "Tell me more and I’ll guide you."
    })

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
