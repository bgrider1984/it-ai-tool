import os
import uuid
from flask import Flask, request, jsonify, session, render_template

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "dev-secret")

sessions = {}

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
            "status": "active"
        }

    return session["sid"]

# ----------------------------
# HELPERS
# ----------------------------
def yes(msg):
    return any(x in msg for x in ["yes", "y", "yeah", "yep"])

def no(msg):
    return any(x in msg for x in ["no", "n", "nope", "still"])

def worked(msg):
    return any(x in msg for x in ["works", "worked", "fine", "ok", "fixed", "good"])

# ----------------------------
# STEP CONTENT
# ----------------------------
steps = [
    "Check keyboard power (batteries / ON switch)",
    "Check wireless interference",
    "Try different USB port",
    "Update keyboard driver",
    "Test keyboard on another computer"
]

def step_text(i):
    return f"Step {i+1}: {steps[i]}"

# ----------------------------
# FINAL PC FIX FLOW
# ----------------------------
def pc_fix():
    return {
        "text": (
            "Since the keyboard works on another computer, the issue is your PC.\n\n"
            "Next steps:\n"
            "• Reset USB power settings\n"
            "• Reinstall USB drivers\n"
            "• Try different USB ports\n\n"
            "Would you like me to walk you through fixing this?"
        ),
        "status": "escalated"
    }

# ----------------------------
# MAIN ENGINE
# ----------------------------
@app.route("/ask", methods=["POST"])
def ask():

    msg = (request.json.get("message") or "").lower()

    sid = get_sid()
    state = sessions[sid]

    # ============================
    # STEP 0 INIT
    # ============================
    if state["step"] == 0:
        state["step"] = 1
        return jsonify({
            "step": 1,
            "response": step_text(0),
            "options": ["Fixed it", "Still broken"]
        })

    # ============================
    # STEPS 1–4
    # ============================
    if 1 <= state["step"] <= 4:

        if yes(msg):
            state["status"] = "resolved"
            return jsonify({
                "status": "resolved",
                "response": "Perfect — glad it’s fixed 👍",
                "options": ["New issue"]
            })

        if no(msg) or "still" in msg:
            state["step"] += 1

            return jsonify({
                "step": state["step"],
                "response": step_text(state["step"] - 1),
                "options": ["Fixed it", "Still broken"]
            })

    # ============================
    # STEP 5 (HARDWARE TEST)
    # ============================
    if state["step"] == 5:

        if worked(msg):
            return jsonify({
                "response": pc_fix()["text"],
                "status": "escalated",
                "options": ["Yes help me fix PC", "No thanks"]
            })

        if no(msg):
            return jsonify({
                "response": "That suggests a hardware failure — replace keyboard.",
                "status": "resolved",
                "options": ["New issue"]
            })

        return jsonify({
            "response": "Did the keyboard work on another computer?",
            "options": ["Yes", "No"]
        })

    # ============================
    # PC FIX FLOW
    # ============================
    if "yes help" in msg or "yes" in msg:

        return jsonify({
            "response": (
                "Step 1: Reset USB power settings\n\n"
                "• Open Device Manager\n"
                "• Expand USB Controllers\n"
                "• Disable USB power saving\n\n"
                "Try again after restart."
            ),
            "status": "active",
            "options": ["Done", "Still broken"]
        })

    # ============================
    # DEFAULT
    # ============================
    return jsonify({
        "response": "Tell me what’s going on and I’ll help.",
        "options": ["Start troubleshooting"]
    })

# ----------------------------
# UI ROUTE
# ----------------------------
@app.route("/")
def home():
    return render_template("dashboard.html")

@app.route("/health")
def health():
    return jsonify({"status": "ok"})

# ----------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
