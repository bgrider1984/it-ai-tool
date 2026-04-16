import os
import uuid
from flask import Flask, request, jsonify, session, redirect, render_template

app = Flask(__name__)

app.secret_key = os.getenv("SECRET_KEY", "dev-secret")

# ----------------------------
# SIMPLE IN-MEMORY STATE
# ----------------------------
sessions = {}

USERS = {
    "admin@local": "admin"
}

# ----------------------------
# GET SESSION
# ----------------------------
def get_sid():
    if "sid" not in session:
        session["sid"] = str(uuid.uuid4())
        sessions[session["sid"]] = {
            "step": 0,
            "history": []
        }

    return session["sid"]

# ----------------------------
# INTENT CLASSIFIER
# ----------------------------
def classify(msg):
    t = msg.lower()

    vague = ["not working", "won't", "broken", "issue", "problem"]
    specific = ["error", "crash", "vpn", "outlook", "blue screen"]

    if any(v in t for v in vague):
        return "clarify"

    if any(s in t for s in specific):
        return "direct"

    return "clarify"

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

    email = data.get("email")
    password = data.get("password")

    if USERS.get(email) != password:
        return jsonify({"error": "invalid login"}), 401

    session["user"] = email
    return jsonify({"status": "ok"})

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

# ----------------------------
# SAFE ASK ROUTE (NO BLANK RESPONSES EVER)
# ----------------------------
@app.route("/ask", methods=["POST"])
def ask():

    try:
        data = request.json or {}
        msg = data.get("message", "")

        if not msg:
            return jsonify({"response": "Please enter a message."})

        sid = get_sid()
        state = sessions[sid]

        state["history"].append(msg)

        step = state["step"]

        # ----------------------------
        # STEP 0 - CLARIFY
        # ----------------------------
        if step == 0:
            reply = (
                "I need a bit more detail:\n\n"
                "• Is this happening to all apps or just one?\n"
                "• Did it start after a restart or update?\n"
                "• Any error messages?"
            )
            state["step"] = 1

        # ----------------------------
        # STEP 1 - INTERPRET
        # ----------------------------
        elif step == 1:

            t = msg.lower()

            if "all" in t:
                reply = "System-wide issue → Check Task Manager (CPU/RAM usage)."

            elif "one" in t:
                reply = "Single-app issue → Try reinstalling or Safe Mode."

            elif "update" in t or "restart" in t:
                reply = "Recent change detected → Consider system restore."

            else:
                reply = "Is this affecting ALL apps or just ONE?"

            state["step"] = 2

        # ----------------------------
        # STEP 2 - FIX
        # ----------------------------
        else:
            reply = (
                "Try these steps:\n\n"
                "1. Restart computer\n"
                "2. Check startup apps\n"
                "3. Run antivirus scan\n"
                "4. Check disk health"
            )

        return jsonify({"response": reply})

    except Exception as e:
        print("ASK ERROR:", str(e))
        return jsonify({
            "response": "⚠ System error occurred. Please try again."
        })

# ----------------------------
# HEALTH CHECK
# ----------------------------
@app.route("/health")
def health():
    return jsonify({
        "status": "ok",
        "sessions": len(sessions)
    })

# ----------------------------
# RUN
# ----------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
