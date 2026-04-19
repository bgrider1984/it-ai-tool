import os
import uuid
from flask import Flask, request, jsonify, session, render_template

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "dev")

# ----------------------------
# SAFE MEMORY STORE
# ----------------------------
db = {}

def get_user():
    if "uid" not in session:
        session["uid"] = str(uuid.uuid4())

    uid = session["uid"]

    if uid not in db:
        db[uid] = {"sessions": {}, "current": None}

    return db[uid]

def new_session(user):
    sid = str(uuid.uuid4())

    user["sessions"][sid] = {
        "id": sid,
        "title": "New Issue",
        "messages": [],
        "state": {
            "route": "unknown",
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
# SAFE CLASSIFIER
# ----------------------------
def classify(msg):
    m = msg.lower()

    if any(x in m for x in ["wifi","internet","router","dns"]):
        return "network"

    if any(x in m for x in ["app","crash","error","software","not opening"]):
        return "software"

    if any(x in m for x in ["keyboard","mouse","usb","battery"]):
        return "hardware"

    return "unknown"

# ----------------------------
# SAFE ROUTER
# ----------------------------
def route(route, step, msg):

    try:

        msg = msg.lower()

        if route == "network":
            if step == 0:
                return {"text":"🌐 Restart your router. Did that fix it?","step":1}
            if step == 1:
                return {"text":"Check if other devices have internet.","step":2}
            return {"text":"Try DNS 8.8.8.8","done":True}

        if route == "software":
            if step == 0:
                return {"text":"🔵 Restart the app. Did that fix it?","step":1}
            if step == 1:
                return {"text":"Reinstall the app. Did that help?","step":2}
            return {"text":"Software issue resolved or needs deeper inspection.","done":True}

        if route == "hardware":
            if step == 0:
                return {"text":"🟢 Check power/batteries. Did that fix it?","step":1}
            return {"text":"Try another USB port or device test.","done":True}

        return {"text":"I need more detail to continue troubleshooting.","done":True}

    except Exception as e:
        return {"text":"⚠ Routing error occurred","done":True}

# ----------------------------
# MAIN API (STABLE CONTRACT)
# ----------------------------
@app.route("/ask", methods=["POST"])
def ask():

    try:
        msg = request.json.get("message","")

        user = get_user()
        session_data = get_session(user)

        # store input
        session_data["messages"].append({"role":"user","text":msg})

        # route logic
        if session_data["state"]["route"] == "unknown":
            session_data["state"]["route"] = classify(msg)

        route_name = session_data["state"]["route"]
        step = session_data["state"]["step"]

        result = route(route_name, step, msg)

        if "step" in result:
            session_data["state"]["step"] = result["step"]

        session_data["messages"].append({
            "role":"bot",
            "text":result["text"]
        })

        # SAFE RESPONSE CONTRACT
        return jsonify({
            "response": result["text"],
            "sessions": list(user["sessions"].values()),
            "debug": {
                "route": route_name,
                "step": session_data["state"]["step"]
            }
        })

    except Exception as e:
        print("CRASH:", e)

        # NEVER FAIL SILENTLY
        return jsonify({
            "response": "⚠ System recovered from error. Please retry.",
            "sessions": [],
            "debug": {
                "route": "error",
                "step": -1
            }
        }), 200

@app.route("/new", methods=["POST"])
def new():
    user = get_user()
    s = new_session(user)
    return jsonify(s)

@app.route("/health")
def health():
    return jsonify({
        "status":"ok",
        "system":"v13-stable"
    })

@app.route("/")
def home():
    return render_template("dashboard.html")

# ----------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
