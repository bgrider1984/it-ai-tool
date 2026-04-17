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
# RESPONSE GUARD (ANTI-LOOP)
# ----------------------------
def safe_response(state, text):
    if state["last_response"] == text:
        return text + "\n\nLet’s try the next step."
    state["last_response"] = text
    return text

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
        "We need to confirm if the keyboard itself is the problem.\n\n"
        "Do this:\n"
        "• Plug the keyboard into another computer\n\n"
        "Results:\n"
        "• If it STILL has issues → keyboard is faulty\n"
        "• If it works fine → problem is your PC\n\n"
        "Tell me what happens."
    )

def step6():
    return (
        "Final Step: System-side fix\n\n"
        "Since hardware seems OK, try this:\n\n"
        "• Open Device Manager\n"
        "• Uninstall the keyboard device\n"
        "• Restart your computer\n\n"
        "Windows will reinstall it automatically.\n\n"
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

    # detect flow
    if state["flow"] is None:
        state["flow"] = detect_flow(msg) or "keyboard"

    # ============================
    # KEYBOARD FLOW
    # ============================
    if state["flow"] == "keyboard":

        # handle "what do I do"
        if "what do i do" in msg:
            if state["step"] == 5:
                return jsonify({"response": safe_response(state, step5())})
            if state["step"] == 6:
                return jsonify({"response": safe_response(state, step6())})

        # STEP 0
        if state["step"] == 0:
            state["step"] = 1
            return jsonify({"response": safe_response(state, step1())})

        # STEP 1
        if state["step"] == 1:
            if "yes" in msg:
                return jsonify({"response": "Great — issue resolved."})
            state["step"] = 2
            return jsonify({"response": safe_response(state, step2())})

        # STEP 2
        if state["step"] == 2:
            if "yes" in msg:
                state["step"] = 3
                return jsonify({"response": safe_response(state, step3())})
            return jsonify({"response": "Good — interference was the issue."})

        # STEP 3
        if state["step"] == 3:
            if "yes" in msg:
                return jsonify({"response": "Great — issue resolved."})
            state["step"] = 4
            return jsonify({"response": safe_response(state, step4())})

        # STEP 4
        if state["step"] == 4:
            if "yes" in msg:
                return jsonify({"response": "Driver update fixed the issue."})
            state["step"] = 5
            return jsonify({"response": safe_response(state, step5())})

        # STEP 5
        if state["step"] == 5:
            if "works fine" in msg:
                state["step"] = 6
                return jsonify({"response": safe_response(state, step6())})

            if "still" in msg or "same" in msg:
                return jsonify({
                    "response": "That confirms the keyboard hardware is failing. Replacing it is recommended."
                })

            return jsonify({
                "response": safe_response(state, "What happened when you tested it on another computer?")
            })

        # STEP 6
        if state["step"] == 6:
            if "yes" in msg:
                return jsonify({"response": "Good — issue resolved."})
            return jsonify({
                "response": "At this point, it may be a deeper OS or hardware issue."
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
