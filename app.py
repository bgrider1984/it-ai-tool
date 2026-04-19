import os
import uuid
from flask import Flask, request, jsonify, session, render_template

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "dev-secret")

# ----------------------------
# GLOBAL STORE
# ----------------------------
users = {}

def get_user():
    if "uid" not in session:
        session["uid"] = str(uuid.uuid4())

    uid = session["uid"]

    if uid not in users:
        users[uid] = {
            "sessions": {},
            "current_session": None
        }

    return users[uid]

def create_session(user):
    sid = str(uuid.uuid4())

    user["sessions"][sid] = {
        "id": sid,
        "name": "New Issue",
        "step": 0,
        "messages": []
    }

    user["current_session"] = sid
    return user["sessions"][sid]

def get_current_session(user):
    sid = user["current_session"]

    if not sid or sid not in user["sessions"]:
        return create_session(user)

    return user["sessions"][sid]

# ----------------------------
# HELPERS
# ----------------------------
def yes(msg):
    return msg in ["y","yes","yeah","yep","fixed","works","working","ok","good"]

def no(msg):
    return msg in ["n","no","nope","still","not"]

# ----------------------------
# CHAT ENGINE
# ----------------------------
def process(session_data, msg):

    step = session_data["step"]

    def add(role, text):
        session_data["messages"].append({"role": role, "text": text})
        return text

    # STEP 0
    if step == 0:
        session_data["step"] = 1
        return add("bot",
            "Step 1: Restart your computer\n\nDid that fix the issue?"
        )

    # STEP 1
    if step == 1:
        if yes(msg):
            return add("bot", "Great — fixed 👍")

        session_data["step"] = 2
        return add("bot",
            "Step 2: Check wireless interference\n\nIs it still happening?"
        )

    # STEP 2
    if step == 2:
        if yes(msg):
            session_data["step"] = 3
            return add("bot",
                "Step 3: Try a different USB port\n\nDid that fix it?"
            )

        return add("bot", "Good — issue resolved 👍")

    # STEP 3
    if step == 3:
        if yes(msg):
            return add("bot", "Great — fixed 👍")

        session_data["step"] = 4
        return add("bot",
            "Step 4: Update keyboard driver\n\nDid that fix it?"
        )

    # STEP 4
    if step == 4:
        if yes(msg):
            return add("bot", "Driver update fixed it 👍")

        session_data["step"] = 5
        return add("bot",
            "Step 5: Test keyboard on another computer\n\nWhat happened?"
        )

    # STEP 5
    if step == 5:
        if "work" in msg:
            session_data["step"] = 6
            return add("bot",
                "Hardware is good. Issue is your PC.\n\nDo you want help fixing it?"
            )

        if no(msg):
            return add("bot", "Keyboard likely faulty — replace it.")

        return add("bot", "Did it work on another computer?")

    # STEP 6
    if step == 6:
        if yes(msg):
            return add("bot",
                "Step: Reset USB power settings\n\nTry again after restart."
            )

        return add("bot", "Okay — start a new issue anytime 👍")

    return add("bot", "Tell me more.")

# ----------------------------
# ROUTES
# ----------------------------
@app.route("/")
def home():
    return render_template("dashboard.html")

@app.route("/ask", methods=["POST"])
def ask():
    try:
        data = request.get_json()
        msg = (data.get("message") or "").lower().strip()

        user = get_user()
        session_data = get_current_session(user)

        # save user msg
        session_data["messages"].append({"role":"user","text":msg})

        reply = process(session_data, msg)

        return jsonify({
            "response": reply,
            "sessions": list(user["sessions"].values()),
            "current": session_data["id"]
        })

    except Exception as e:
        print("ERROR:", e)
        return jsonify({"response":"⚠ Server error"}), 500

@app.route("/sessions")
def sessions_route():
    user = get_user()
    return jsonify(list(user["sessions"].values()))

@app.route("/switch_session", methods=["POST"])
def switch_session():
    user = get_user()
    sid = request.json.get("sid")

    if sid in user["sessions"]:
        user["current_session"] = sid

    return jsonify({"status":"ok"})

@app.route("/new_session", methods=["POST"])
def new_session():
    user = get_user()
    s = create_session(user)
    return jsonify(s)

@app.route("/health")
def health():
    return jsonify({"status":"ok"})

# ----------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
