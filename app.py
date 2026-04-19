import os
import uuid
from flask import Flask, request, jsonify, session, render_template

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "dev-secret")

# ----------------------------
# MEMORY
# ----------------------------
users = {}

def get_user():
    if "uid" not in session:
        session["uid"] = str(uuid.uuid4())

    uid = session["uid"]

    if uid not in users:
        users[uid] = {
            "step": 0,
            "last_question": None,
            "resolved": False
        }

    return users[uid]

# ----------------------------
# INTENT DETECTION
# ----------------------------
def detect_answer(msg):
    msg = msg.lower()

    if any(x in msg for x in ["yes","y","yeah","yep"]):
        return "yes"

    if any(x in msg for x in ["no","n","nope","still"]):
        return "no"

    if any(x in msg for x in ["works","fixed","good","resolved"]):
        return "fixed"

    return "unknown"

# ----------------------------
# ENGINE
# ----------------------------
def troubleshoot(state, msg):

    answer = detect_answer(msg)

    # ---------------- STEP 0
    if state["step"] == 0:
        state["step"] = 1
        state["last_question"] = "restart"

        return "Step 1:\nRestart your computer.\n\nDid that fix the issue?"

    # ---------------- STEP 1 (Restart)
    if state["step"] == 1:

        if answer in ["yes","fixed"]:
            state["resolved"] = True
            return "Great — restarting fixed it 👍"

        state["step"] = 2
        state["last_question"] = "all_apps"

        return (
            "Step 2:\n"
            "Is this happening to ALL apps or just one?\n\n"
            "Reply: 'all' or 'one'"
        )

    # ---------------- STEP 2 (Scope)
    if state["step"] == 2:

        if "all" in msg:
            state["step"] = 3
            state["last_question"] = "task_manager"

            return (
                "Step 3:\n"
                "Check system usage.\n\n"
                "Press Ctrl + Shift + Esc\n"
                "Look at CPU and Memory.\n\n"
                "Tell me the percentages."
            )

        if "one" in msg:
            state["resolved"] = True
            return "This is likely an app-specific issue. Reinstall that app."

        return "Is it ALL apps or just ONE?"

    # ---------------- STEP 3 (Usage)
    if state["step"] == 3:

        if "%" in msg:
            state["step"] = 4
            state["last_question"] = "high_usage"

            return (
                "Step 4:\n"
                "Sort processes by Memory usage.\n\n"
                "Tell me the top process using memory."
            )

        return "Tell me CPU % and Memory % (example: CPU 80%, Memory 95%)"

    # ---------------- STEP 4 (Process)
    if state["step"] == 4:

        if len(msg) > 2:
            state["step"] = 5
            state["last_question"] = "safe_kill"

            return (
                "Step 5:\n"
                "That process may be causing the issue.\n\n"
                "Right-click it → End Task (only if not system process)\n\n"
                "Did that fix the issue?"
            )

        return "Tell me the process name."

    # ---------------- STEP 5 (Kill)
    if state["step"] == 5:

        if answer in ["yes","fixed"]:
            state["resolved"] = True
            return "Perfect — that process was the problem 👍"

        state["step"] = 6
        state["last_question"] = "safe_mode"

        return (
            "Step 6:\n"
            "Restart into Safe Mode.\n\n"
            "Does the issue still happen there?"
        )

    # ---------------- STEP 6 (Safe Mode)
    if state["step"] == 6:

        if answer == "no":
            state["resolved"] = True
            return (
                "Good — that means a startup program is causing it.\n\n"
                "Disable startup apps."
            )

        if answer == "yes":
            state["step"] = 7
            return (
                "Step 7:\n"
                "Run System File Checker:\n\n"
                "Open Command Prompt as admin\n"
                "Run: sfc /scannow\n\n"
                "Tell me what it says."
            )

        return "Does it still happen in Safe Mode? (yes/no)"

    return "Tell me more about the issue."

# ----------------------------
# ROUTES
# ----------------------------
@app.route("/")
def home():
    return render_template("dashboard.html")

@app.route("/ask", methods=["POST"])
def ask():
    try:
        msg = (request.json.get("message") or "").strip()

        user = get_user()
        reply = troubleshoot(user, msg)

        return jsonify({"response": reply})

    except Exception as e:
        print("ERROR:", e)
        return jsonify({"response": "⚠ Server error"}), 500

@app.route("/health")
def health():
    return jsonify({"status":"ok"})

# ----------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
