import os
import uuid
from flask import Flask, request, jsonify, session, render_template

# =========================
# APP INIT (MUST BE FIRST)
# =========================
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "dev-secret")

# =========================
# MEMORY STORE (TEMP FOR NOW)
# =========================
db = {}

# =========================
# USER SESSION HANDLING
# =========================
def get_user():
    if "uid" not in session:
        session["uid"] = str(uuid.uuid4())

    uid = session["uid"]

    if uid not in db:
        db[uid] = {
            "sessions": {},
            "current": None
        }

    return db[uid]


def new_session(user):
    sid = str(uuid.uuid4())

    user["sessions"][sid] = {
        "id": sid,
        "title": "New Issue",
        "messages": [],
        "state": {
            "route": None,
            "step": 0
        }
    }

    user["current"] = sid
    return user["sessions"][sid]


def get_session(user):
    sid = user["current"]

    if not sid or sid not in user["sessions"]:
        return new_session(user)

    return user["sessions"][sid]

# =========================
# ISSUE CLASSIFIER
# =========================
def classify_issue(msg):
    msg = msg.lower()

    if any(x in msg for x in ["wifi","internet","router","dns","network"]):
        return "network"

    if any(x in msg for x in ["app","error","crash","won't open","software"]):
        return "software"

    if any(x in msg for x in ["keyboard","mouse","usb","battery","hardware"]):
        return "hardware"

    return "unknown"

# =========================
# ROUTING ENGINE
# =========================
def route_step(route, step, msg):

    msg = msg.lower()

    # ---------------- NETWORK
    if route == "network":

        if step == 0:
            return {
                "text": "🌐 Step 1: Restart your router\n\nDid that fix the issue?",
                "step": 1
            }

        if step == 1:
            if "yes" in msg:
                return {"text": "Great — network restored 👍", "done": True}

            return {
                "text": "Step 2: Check if other devices have internet.\nDo they?",
                "step": 2
            }

        if step == 2:
            return {"text": "Try changing DNS to 8.8.8.8", "done": True}

    # ---------------- SOFTWARE
    if route == "software":

        if step == 0:
            return {
                "text": "🔵 Step 1: Restart the app\n\nDid that fix it?",
                "step": 1
            }

        if step == 1:
            if "no" in msg:
                return {
                    "text": "Step 2: Reinstall the app\n\nDid that help?",
                    "step": 2
                }

            return {"text": "Fixed 👍", "done": True}

    # ---------------- HARDWARE
    if route == "hardware":

        if step == 0:
            return {
                "text": "🟢 Step 1: Check power / batteries\n\nDid that fix it?",
                "step": 1
            }

        if step == 1:
            return {"text": "Try another USB port or device test.", "done": True}

    # ---------------- UNKNOWN
    return {
        "text": "I need more details to continue troubleshooting.",
        "done": True
    }

# =========================
# ROUTES
# =========================

@app.route("/")
def home():
    return render_template("dashboard.html")


@app.route("/ask", methods=["POST"])
def ask():

    try:
        msg = request.json.get("message", "").strip()

        user = get_user()
        session_data = get_session(user)

        # store user message
        session_data["messages"].append({
            "role": "user",
            "text": msg
        })

        # assign route if first message
        if not session_data["state"]["route"]:
            session_data["state"]["route"] = classify_issue(msg)

        route = session_data["state"]["route"]
        step = session_data["state"]["step"]

        result = route_step(route, step, msg)

        if "step" in result:
            session_data["state"]["step"] = result["step"]

        # store bot response
        session_data["messages"].append({
            "role": "bot",
            "text": result["text"]
        })

        return jsonify({
            "response": result["text"],
            "sessions": list(user["sessions"].values())
        })

    except Exception as e:
        print("ERROR:", e)
        return jsonify({"response": "⚠ Server error"}), 500


@app.route("/new", methods=["POST"])
def new():
    user = get_user()
    s = new_session(user)
    return jsonify(s)


@app.route("/sessions")
def sessions():
    user = get_user()
    return jsonify(list(user["sessions"].values()))


@app.route("/health")
def health():
    return jsonify({
        "status": "ok",
        "version": "v11-safe-deploy"
    })


# =========================
# MAIN
# =========================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
