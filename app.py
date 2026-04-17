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
            "last_q": None,
            "last_response": ""
        }

    return session["sid"]

# ----------------------------
# INTENT HELPERS
# ----------------------------
def is_yes(msg):
    return any(x in msg for x in ["yes", "y", "yeah", "yep"])

def is_no(msg):
    return any(x in msg for x in ["no", "n", "nope", "still", "not"])

def is_positive_result(msg):
    return any(x in msg for x in [
        "it works", "works", "fine", "ok", "okay", "good", "fixed", "resolved"
    ])

def safe_response(state, text):
    if state["last_response"] == text:
        return text + "\n\nAre you still seeing the issue?"
    state["last_response"] = text
    return text

# ----------------------------
# FLOW DETECTION
# ----------------------------
def detect_flow(msg):
    if "keyboard" in msg:
        return "keyboard"
    return "keyboard"

# ----------------------------
# STEPS
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
        "• Plug receiver into another port\n\n"
        "Did that fix the issue?"
    )

def step4():
    return (
        "Step 4: Update keyboard driver\n\n"
        "• Device Manager → Keyboards\n"
        "• Update driver\n\n"
        "Restart PC\n\n"
        "Did that fix the issue?"
    )

def step5():
    return (
        "Step 5: Hardware test\n\n"
        "• Plug keyboard into another computer\n\n"
        "Tell me what happened."
    )

def final_fix():
    return (
        "Great — since it works on another computer, the keyboard is OK.\n\n"
        "This means the issue is with your PC configuration.\n\n"
        "Next steps:\n"
        "• Reinstall USB drivers\n"
        "• Check USB power settings\n"
        "• Try different USB port types\n\n"
        "Do you want me to walk you through fixing the PC side next?"
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

    # ============================
    # STEP 1
    # ============================
    if state["step"] == 0:
        state["step"] = 1
        state["last_q"] = "fixed"
        return jsonify({"response": safe_response(state, step1())})

    # ============================
    # STEP 2
    # ============================
    if state["step"] == 1:
        if is_yes(msg):
            return jsonify({"response": "Great — issue resolved."})

        state["step"] = 2
        state["last_q"] = "still"
        return jsonify({"response": safe_response(state, step2())})

    # ============================
    # STEP 3
    # ============================
    if state["step"] == 2:
        if is_yes(msg):  # still happening
            state["step"] = 3
            state["last_q"] = "fixed"
            return jsonify({"response": safe_response(state, step3())})

        return jsonify({"response": "Good — interference fixed it."})

    # ============================
    # STEP 4
    # ============================
    if state["step"] == 3:
        if is_yes(msg):
            return jsonify({"response": "Great — issue resolved."})

        state["step"] = 4
        return jsonify({"response": safe_response(state, step4())})

    # ============================
    # STEP 5
    # ============================
    if state["step"] == 4:
        if is_positive_result(msg):
            state["step"] = 5
            return jsonify({"response": safe_response(state, step5())})

        if is_no(msg):
            state["step"] = 5
            return jsonify({"response": safe_response(state, step5())})

        return jsonify({"response": "Tell me what happened when you tested it."})

    # ============================
    # FINAL STEP (FIXED LOGIC)
    # ============================
    if state["step"] == 5:

        if is_positive_result(msg):
            state["step"] = 6
            return jsonify({"response": final_fix()})

        if "still" in msg or is_no(msg):
            return jsonify({
                "response": "That confirms a hardware issue — the keyboard likely needs replacement."
            })

        # CRITICAL FIX: stop looping same question
        return jsonify({
            "response": "Just to confirm — did it work correctly on the other computer?"
        })

    # ============================
    # END STATE
    # ============================
    if state["step"] >= 6:
        return jsonify({
            "response": "We’ve completed troubleshooting. Let me know if you want deeper PC diagnostics."
        })

    return jsonify({"response": "Tell me more about the issue."})

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
