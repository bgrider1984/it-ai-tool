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
            "flow": None
        }

    return session["sid"]

# ----------------------------
# DETECT FLOW
# ----------------------------
def detect_flow(msg):
    t = msg.lower()

    if "keyboard" in t:
        return "keyboard"
    if "app" in t:
        return "apps"

    return "general"

# ----------------------------
# KEYBOARD STEPS
# ----------------------------
def keyboard_step_1():
    return (
        "Step 1: Check keyboard power\n\n"
        "If wireless:\n"
        "• Replace batteries with NEW ones\n"
        "• Make sure power switch is ON\n\n"
        "If using USB receiver:\n"
        "• Unplug and plug it back in\n\n"
        "Did that fix the issue?"
    )

def keyboard_step_2():
    return (
        "Step 2: Check signal interference\n\n"
        "• Move keyboard closer to PC\n"
        "• Remove nearby wireless devices temporarily\n\n"
        "Does the issue still happen?"
    )

def keyboard_step_3():
    return (
        "Step 3: Check USB receiver\n\n"
        "• Plug receiver into a different USB port\n"
        "• Prefer ports on the back of the PC\n\n"
        "Did that change anything?"
    )

def keyboard_step_4():
    return (
        "Step 4: Check keyboard drivers\n\n"

        "Open Device Manager:\n"
        "• Right-click Start\n"
        "• Click 'Device Manager'\n\n"

        "Find your keyboard:\n"
        "• Expand 'Keyboards'\n"
        "• Right-click your keyboard → 'Update driver'\n\n"

        "Then:\n"
        "• Click 'Search automatically for drivers'\n\n"

        "After that:\n"
        "• Restart your computer\n\n"

        "Did that fix the issue?"
    )

def keyboard_step_5():
    return (
        "Step 5: Reinstall keyboard driver\n\n"

        "In Device Manager:\n"
        "• Right-click your keyboard\n"
        "• Click 'Uninstall device'\n\n"

        "Then:\n"
        "• Restart your computer\n\n"

        "What happens:\n"
        "• Windows will reinstall the driver automatically\n\n"

        "Did that fix the issue?"
    )

def keyboard_step_6():
    return (
        "Step 6: Hardware check\n\n"

        "Test this:\n"
        "• Try the keyboard on another computer\n\n"

        "If it still has the issue:\n"
        "• The keyboard hardware is likely failing\n\n"

        "If it works fine elsewhere:\n"
        "• The issue is with your PC configuration\n\n"

        "Tell me what happened."
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

    # detect flow once
    if state["flow"] is None:
        state["flow"] = detect_flow(msg)

    # ============================
    # KEYBOARD FLOW
    # ============================
    if state["flow"] == "keyboard":

        if state["step"] == 0:
            state["step"] = 1
            return jsonify({"response": keyboard_step_1()})

        if state["step"] == 1:
            if "yes" in msg:
                return jsonify({"response": "Great — issue resolved."})
            state["step"] = 2
            return jsonify({"response": keyboard_step_2()})

        if state["step"] == 2:
            if "no" in msg or "still" in msg:
                state["step"] = 3
                return jsonify({"response": keyboard_step_3()})
            return jsonify({"response": "Good — sounds like interference was the issue."})

        if state["step"] == 3:
            if "no" in msg or "still" in msg:
                state["step"] = 4
                return jsonify({"response": keyboard_step_4()})
            return jsonify({"response": "Good — USB port was the issue."})

        if state["step"] == 4:
            if "yes" in msg:
                return jsonify({"response": "Great — driver update fixed it."})
            state["step"] = 5
            return jsonify({"response": keyboard_step_5()})

        if state["step"] == 5:
            if "yes" in msg:
                return jsonify({"response": "Good — reinstall fixed the issue."})
            state["step"] = 6
            return jsonify({"response": keyboard_step_6()})

        if state["step"] == 6:
            return jsonify({
                "response": "Based on that result, we can determine whether this is hardware or system related."
            })

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
