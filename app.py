import os
import uuid
from flask import Flask, request, jsonify, session, render_template

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "dev")

# =========================
# MEMORY STORE (TEMP)
# =========================
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
            "route": None,
            "history_signals": []
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
# ISSUE DETECTION
# =========================
def classify(msg):
    m = msg.lower()

    if any(x in m for x in ["wifi","internet","router","dns"]):
        return "network"

    if any(x in m for x in ["app","crash","error","not working","software"]):
        return "software"

    if any(x in m for x in ["mouse","keyboard","usb","battery","hardware"]):
        return "hardware"

    return "unknown"

# =========================
# SMART SIGNAL DETECTOR
# =========================
def detect_signal(msg):

    m = msg.lower()

    signals = []

    if any(x in m for x in ["no","still","same","not working","yep","y"]):
        signals.append("persistent_issue")

    if any(x in m for x in ["ok","fixed","works","done","yes"]):
        signals.append("resolved_signal")

    if any(x in m for x in ["what","huh","confused","repeat"]):
        signals.append("confusion")

    return signals

# =========================
# ADAPTIVE REASONING CORE
# =========================
def reason(route, session_state, msg):

    signals = detect_signal(msg)
    history = session_state["history_signals"]

    # store signals
    history.extend(signals)

    # ------------------------
    # ESCALATION / LOOP BREAK
    # ------------------------
    if history.count("persistent_issue") >= 2:
        return {
            "text": "⚠ It looks like basic troubleshooting is not resolving this.\nThis may require advanced diagnostics or hardware inspection.",
            "done": True
        }

    # ------------------------
    # NETWORK
    # ------------------------
    if route == "network":

        if "resolved_signal" in signals:
            return {"text":"✔ Network issue appears resolved.","done":True}

        if "persistent_issue" in signals:
            return {
                "text":"Next step: test another device on same network.\nThis helps isolate router vs ISP issues.",
                "done": False
            }

        return {
            "text":"🌐 Step: Restart your router.\nDid that improve the connection?",
            "done": False
        }

    # ------------------------
    # SOFTWARE
    # ------------------------
    if route == "software":

        if "resolved_signal" in signals:
            return {"text":"✔ Software issue appears resolved.","done":True}

        if "persistent_issue" in signals:
            return {
                "text":"Next step: clear application cache or reinstall.\nLet me know if it still fails.",
                "done": False
            }

        return {
            "text":"🔵 Step: Restart the application.\nDid that fix the issue?",
            "done": False
        }

    # ------------------------
    # HARDWARE
    # ------------------------
    if route == "hardware":

        if "resolved_signal" in signals:
            return {"text":"✔ Hardware issue appears resolved.","done":True}

        if "persistent_issue" in signals:
            return {
                "text":"Next step: test device on another computer.\nThis isolates hardware vs system issue.",
                "done": False
            }

        return {
            "text":"🟢 Step: Check power or batteries.\nIs the issue still happening?",
            "done": False
        }

    # ------------------------
    # UNKNOWN
    # ------------------------
    return {
        "text":"I need more details to diagnose the issue properly.",
        "done": True
    }

# =========================
# API
# =========================
@app.route("/ask", methods=["POST"])
def ask():

    msg = request.json.get("message","")

    user = get_user()
    session_data = get_session(user)

    # store input
    session_data["messages"].append({"role":"user","text":msg})

    if not session_data["state"]["route"]:
        session_data["state"]["route"] = classify(msg)

    route = session_data["state"]["route"]

    result = reason(route, session_data["state"], msg)

    session_data["messages"].append({
        "role":"bot",
        "text":result["text"]
    })

    return jsonify({
        "response": result["text"],
        "sessions": list(user["sessions"].values())
    })


@app.route("/new", methods=["POST"])
def new():
    user = get_user()
    return jsonify(new_session(user))


@app.route("/health")
def health():
    return jsonify({"status":"ok","version":"v15-adaptive-reasoning"})


@app.route("/")
def home():
    return render_template("dashboard.html")

# =========================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
