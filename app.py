import os
import uuid
from flask import Flask, request, jsonify, session, render_template

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "dev-secret")

# ----------------------------
# PERSISTENT MEMORY (V9)
# ----------------------------
db = {}

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

# ----------------------------
# INTELLIGENCE ROUTER (V9 CORE)
# ----------------------------
def classify_issue(msg):

    msg = msg.lower()

    if any(k in msg for k in ["wifi","internet","dns","network","router"]):
        return "network"

    if any(k in msg for k in ["blue screen","crash","app","software","won't open","error"]):
        return "software"

    if any(k in msg for k in ["keyboard","mouse","usb","battery","hardware"]):
        return "hardware"

    return "unknown"

def route_step(route, step, msg):

    # ---------------- NETWORK ROUTE
    if route == "network":

        if step == 0:
            return {
                "text": "🌐 Network Issue Detected\n\nStep 1: Restart your router\n\nDid that fix it?",
                "step": 1
            }

        if step == 1:
            if "yes" in msg:
                return {"text": "Great — network restored 👍", "done": True}

            return {
                "text": "Step 2: Check if other devices have internet\n\nDo they?",
                "step": 2
            }

        if step == 2:
            return {"text": "Try changing DNS to 8.8.8.8", "done": True}

    # ---------------- SOFTWARE ROUTE
    if route == "software":

        if step == 0:
            return {
                "text": "🔵 Software Issue Detected\n\nStep 1: Restart the application\n\nDid that fix it?",
                "step": 1
            }

        if step == 1:
            if "no" in msg:
                return {
                    "text": "Step 2: Reinstall the application\n\nDid that help?",
                    "step": 2
                }

            return {"text": "Fixed 👍", "done": True}

    # ---------------- HARDWARE ROUTE
    if route == "hardware":

        if step == 0:
            return {
                "text": "🟢 Hardware Issue Detected\n\nStep 1: Check power / batteries\n\nDid that fix it?",
                "step": 1
            }

        if step == 1:
            return {"text": "Try a different port or device test.", "done": True}

    # ---------------- UNKNOWN ROUTE
    return {
        "text": "I need more info — what exactly is happening?",
        "done": True
    }

# ----------------------------
# MAIN AI ENTRY
# ----------------------------
@app.route("/ask", methods=["POST"])
def ask():
    try:

        msg = request.json.get("message", "").strip().lower()

        user = get_user()
        session_data = get_session(user)

        # store message
        session_data["messages"].append({"role":"user","text":msg})

        # classify
        route = session_data["state"]["route"]
        step = session_data["state"]["step"]

        if not route:
            route = classify_issue(msg)
            session_data["state"]["route"] = route

        result = route_step(route, step, msg)

        # update state
        if "step" in result:
            session_data["state"]["step"] = result["step"]

        # store response
        session_data["messages"].append({"role":"bot","text":result["text"]})

        return jsonify({
            "response": result["text"],
            "route": route,
            "sessions": list(user["sessions"].values())
        })

    except Exception as e:
        print("ERROR:", e)
        return jsonify({"response":"⚠ Server error"}), 500

# ----------------------------
@app.route("/sessions")
def sessions():
    user = get_user()
    return jsonify(list(user["sessions"].values()))

@app.route("/switch", methods=["POST"])
def switch():
    user = get_user()
    sid = request.json.get("sid")
    if sid in user["sessions"]:
        user["current"] = sid
    return jsonify({"ok": True})

@app.route("/new", methods=["POST"])
def new():
    user = get_user()
    s = new_session(user)
    return jsonify(s)

@app.route("/")
def home():
    return render_template("dashboard.html")

@app.route("/health")
def health():
    return jsonify({"status":"ok","v":"v9-routing"})

# ----------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
