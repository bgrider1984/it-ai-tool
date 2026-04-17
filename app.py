import os
import uuid
from flask import Flask, request, jsonify, session, render_template

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "dev-secret")

# ----------------------------
# SESSION STORE (in-memory)
# ----------------------------
sessions = {}

def get_sid():
    if "sid" not in session:
        sid = str(uuid.uuid4())
        session["sid"] = sid

        sessions[sid] = {
            "step": 0,
            "status": "active",
            "flow": None
        }

    return session["sid"]

# ----------------------------
# HELPERS
# ----------------------------
def is_yes(msg):
    return any(x in msg for x in ["yes", "y", "yeah", "yep", "fixed", "works", "good"])

def is_no(msg):
    return any(x in msg for x in ["no", "n", "nope", "still", "not"])

def is_working(msg):
    return any(x in msg for x in ["works", "working", "fine", "ok", "okay", "resolved"])

# ----------------------------
# FLOW DETECTION
# ----------------------------
def detect_flow(msg):
    msg = msg.lower()
    if "keyboard" in msg:
        return "keyboard"
    return "general"

# ----------------------------
# STEPS (KEYBOARD FLOW)
# ----------------------------
def step_text(step):
    steps = {
        1: "Step 1: Check keyboard power\n• Replace batteries\n• Make sure keyboard is ON\n\nDid that fix the issue?",
        2: "Step 2: Check wireless interference\n• Move keyboard closer\n• Remove nearby wireless devices\n\nIs the issue still happening?",
        3: "Step 3: Try another USB port\n• Plug receiver into different USB port\n\nDid that fix the issue?",
        4: "Step 4: Update keyboard driver\n• Device Manager → Keyboards\n• Update driver\n• Restart PC\n\nDid that fix the issue?",
        5: "Step 5: Hardware test\n• Test keyboard on another computer\n\nTell me what happened."
    }
    return steps.get(step, "Let’s continue troubleshooting.")

# ----------------------------
# MAIN CHAT ENGINE
# ----------------------------
@app.route("/ask", methods=["POST"])
def ask():

    msg = (request.json.get("message") or "").lower()

    sid = get_sid()
    state = sessions[sid]

    # initialize flow
    if state["flow"] is None:
        state["flow"] = detect_flow(msg)

    # ----------------------------
    # STEP 0 → START
    # ----------------------------
    if state["step"] == 0:
        state["step"] = 1
        return jsonify({
            "step": 1,
            "response": step_text(1),
            "options": ["Yes", "No"]
        })

    # ----------------------------
    # STEP 1
    # ----------------------------
    if state["step"] == 1:

        if is_yes(msg):
            return jsonify({
                "status": "resolved",
                "response": "Great — glad it’s fixed 👍",
                "options": ["New issue"]
            })

        state["step"] = 2
        return jsonify({
            "step": 2,
            "response": step_text(2),
            "options": ["Yes", "No"]
        })

    # ----------------------------
    # STEP 2
    # ----------------------------
    if state["step"] == 2:

        if is_yes(msg):  # still happening
            state["step"] = 3
            return jsonify({
                "step": 3,
                "response": step_text(3),
                "options": ["Yes", "No"]
            })

        return jsonify({
            "status": "resolved",
            "response": "Great — interference was likely the cause 👍",
            "options": ["New issue"]
        })

    # ----------------------------
    # STEP 3
    # ----------------------------
    if state["step"] == 3:

        if is_yes(msg):
            return jsonify({
                "status": "resolved",
                "response": "Great — issue fixed 👍",
                "options": ["New issue"]
            })

        state["step"] = 4
        return jsonify({
            "step": 4,
            "response": step_text(4),
            "options": ["Yes", "No"]
        })

    # ----------------------------
    # STEP 4
    # ----------------------------
    if state["step"] == 4:

        if is_yes(msg):
            return jsonify({
                "status": "resolved",
                "response": "Driver update fixed it 👍",
                "options": ["New issue"]
            })

        state["step"] = 5
        return jsonify({
            "step": 5,
            "response": step_text(5),
            "options": ["Worked", "Did not work"]
        })

    # ----------------------------
    # STEP 5 (IMPORTANT FIX HERE)
    # ----------------------------
    if state["step"] == 5:

        # FIXED: proper recognition of success
        if is_working(msg) or is_yes(msg):
            state["step"] = 6
            return jsonify({
                "status": "escalated",
                "response":
                    "Great — the keyboard works on another computer.\n\n"
                    "This confirms the issue is with your PC.\n\n"
                    "Next steps:\n"
                    "• USB power settings reset\n"
                    "• Reinstall USB drivers\n"
                    "• Try different USB ports\n\n"
                    "Do you want help fixing your PC?",
                "options": ["Yes", "No"]
            })

        if is_no(msg):
            return jsonify({
                "status": "resolved",
                "response": "That suggests a hardware failure — replace keyboard.",
                "options": ["New issue"]
            })

        return jsonify({
            "step": 5,
            "response": step_text(5),
            "options": ["Worked", "Still broken"]
        })

    # ----------------------------
    # STEP 6 (ESCALATION)
    # ----------------------------
    if state["step"] == 6:

        if is_yes(msg):
            return jsonify({
                "response":
                    "Step 1: Reset USB power settings\n"
                    "• Open Device Manager\n"
                    "• Expand USB Controllers\n"
                    "• Disable power saving\n\n"
                    "Try again and tell me if it works.",
                "options": ["Done", "Still broken"]
            })

        if is_no(msg):
            return jsonify({
                "status": "resolved",
                "response": "Okay — feel free to start a new issue anytime 👍",
                "options": ["New issue"]
            })

        return jsonify({
            "response": "Do you want help fixing the PC issue?",
            "options": ["Yes", "No"]
        })

    return jsonify({
        "response": "Tell me what’s going on and I’ll help."
    })

# ----------------------------
# ROUTES (FIXED)
# ----------------------------
@app.route("/")
def home():
    return render_template("dashboard.html")

@app.route("/dashboard")
def dashboard():
    return render_template("dashboard.html")

@app.route("/health")
def health():
    return jsonify({"status": "ok"})

# ----------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
