import os
import uuid
from flask import Flask, request, jsonify, session, redirect, render_template

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "dev-secret")

sessions = {}
USERS = {"admin@local": "admin"}

# ----------------------------
# SESSION
# ----------------------------
def get_sid():
    if "sid" not in session:
        sid = str(uuid.uuid4())
        session["sid"] = sid
        sessions[sid] = {
            "step": 0,
            "last_q": None,
            "last_response": "",
            "locked": False
        }
    return session["sid"]

# ----------------------------
# CLASSIFIERS
# ----------------------------
def is_yes(msg):
    return any(x in msg for x in ["yes", "y", "yeah", "yep"])

def is_no(msg):
    return any(x in msg for x in ["no", "n", "nope", "still", "not"])

def is_positive(msg):
    return any(x in msg for x in ["worked", "works", "fine", "ok", "good", "fixed"])

# ----------------------------
# HARD LOCK GUARD
# ----------------------------
def respond(state, text):
    """
    Ensures ONLY ONE response per request.
    Prevents repeated looping output.
    """
    if state["locked"]:
        return None

    state["locked"] = True
    state["last_response"] = text
    return text

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
        "• Remove wireless devices\n\n"
        "Is it still happening?"
    )

def step3():
    return (
        "Step 3: Try another USB port\n\n"
        "• Plug receiver into different port\n\n"
        "Did that fix the issue?"
    )

def step4():
    return (
        "Step 4: Update driver\n\n"
        "• Device Manager → Keyboards\n"
        "• Update driver\n"
        "• Restart PC\n\n"
        "Did that fix the issue?"
    )

def step5():
    return (
        "Step 5: Hardware test\n\n"
        "• Test keyboard on another computer\n\n"
        "Tell me what happened."
    )

def final_fix():
    return (
        "Great — since it works on another computer:\n\n"
        "✔ Keyboard hardware is GOOD\n"
        "❌ Issue is with your PC\n\n"
        "Next steps:\n"
        "• USB power settings reset\n"
        "• Driver reinstall\n"
        "• Try different USB port\n\n"
        "Do you want help fixing the PC side?"
    )

# ----------------------------
# MAIN ENGINE
# ----------------------------
@app.route("/ask", methods=["POST"])
def ask():

    msg = (request.json.get("message") or "").lower()

    sid = get_sid()
    state = sessions[sid]

    # RESET LOCK EACH REQUEST (IMPORTANT)
    state["locked"] = False

    # ============================
    # STEP 0 → STEP 1
    # ============================
    if state["step"] == 0:
        state["step"] = 1
        return jsonify({"response": respond(state, step1())})

    # ============================
    # STEP 1
    # ============================
    if state["step"] == 1:
        if is_yes(msg):
            return jsonify({"response": respond(state, "Great — issue resolved 👍")})

        state["step"] = 2
        return jsonify({"response": respond(state, step2())})

    # ============================
    # STEP 2
    # ============================
    if state["step"] == 2:
        if is_yes(msg):  # still happening
            state["step"] = 3
            return jsonify({"response": respond(state, step3())})

        return jsonify({"response": respond(state, "Good — issue appears resolved.")})

    # ============================
    # STEP 3
    # ============================
    if state["step"] == 3:
        if is_yes(msg):
            return jsonify({"response": respond(state, "Fixed 👍")})

        state["step"] = 4
        return jsonify({"response": respond(state, step4())})

    # ============================
    # STEP 4
    # ============================
    if state["step"] == 4:
        if is_yes(msg):
            return jsonify({"response": respond(state, "Driver fix worked 👍")})

        state["step"] = 5
        return jsonify({"response": respond(state, step5())})

    # ============================
    # STEP 5 (CRITICAL FIX HERE)
    # ============================
    if state["step"] == 5:

        # FIXED: ANY positive result = FINALIZE immediately
        if is_positive(msg):
            state["step"] = 6
            return jsonify({"response": respond(state, final_fix())})

        if is_no(msg):
            return jsonify({"response": respond(state, "That suggests hardware failure — replacement likely needed.")})

        # IMPORTANT: no repetition loop allowed anymore
        state["step"] = 6
        return jsonify({"response": respond(state, final_fix())})

    # ============================
    # END STATE
    # ============================
    if state["step"] >= 6:
        return jsonify({
            "response": "Troubleshooting complete. Let me know if you want to fix another issue."
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
