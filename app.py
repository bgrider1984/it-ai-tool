import os
import uuid
from flask import Flask, request, jsonify, session, render_template

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "dev-secret")

# ----------------------------
# SESSION STORE
# ----------------------------
sessions = {}

def get_state():
    if "sid" not in session:
        sid = str(uuid.uuid4())
        session["sid"] = sid
        sessions[sid] = {"step": 0}

    return sessions[session["sid"]]

# ----------------------------
# HELPERS
# ----------------------------
def yes(msg):
    return msg in ["y","yes","yeah","yep","fixed","works","working","ok","good"]

def no(msg):
    return msg in ["n","no","nope","still","not"]

def contains(msg, words):
    return any(w in msg for w in words)

# ----------------------------
# MAIN ENGINE (SAFE)
# ----------------------------
@app.route("/ask", methods=["POST"])
def ask():
    try:
        data = request.get_json(force=True)
        msg = (data.get("message") or "").lower().strip()

        state = get_state()
        step = state["step"]

        print(f"[DEBUG] Step: {step}, Msg: {msg}")

        # ---------------- STEP 0
        if step == 0:
            state["step"] = 1
            return jsonify({
                "response": "Step 1: Restart your computer\n\nDid that fix the issue?",
                "step": 1,
                "options": ["Yes","No"]
            })

        # ---------------- STEP 1
        if step == 1:
            if yes(msg):
                return jsonify({"response": "Great — fixed 👍"})
            state["step"] = 2
            return jsonify({
                "response": "Step 2: Check wireless interference\n\nIs it still happening?",
                "step": 2,
                "options": ["Yes","No"]
            })

        # ---------------- STEP 2
        if step == 2:
            if yes(msg):
                state["step"] = 3
                return jsonify({
                    "response": "Step 3: Try different USB port\n\nDid that fix it?",
                    "step": 3,
                    "options": ["Yes","No"]
                })
            return jsonify({"response": "Good — resolved 👍"})

        # ---------------- STEP 3
        if step == 3:
            if yes(msg):
                return jsonify({"response": "Great — fixed 👍"})
            state["step"] = 
