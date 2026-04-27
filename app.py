from flask import Flask, render_template, request, jsonify, session, redirect
from openai import OpenAI
import os, uuid, subprocess, platform

app = Flask(__name__)
app.secret_key = "dev-secret"

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
MODEL = "gpt-4.1-mini"

# ---------------- DATA ----------------
USERS = {}
CHAT_MEMORY = {}
CASE_MEMORY = {}
SESSION_STORE = {}
ANALYTICS = {
    "issues": {},
    "fixes_run": 0
}

# ---------------- AUTH ----------------
@app.route("/", methods=["GET","POST"])
def login():
    if request.method == "POST":
        user = request.form.get("username")
        session["user"] = user
        return redirect("/dashboard")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

# ---------------- SESSION ----------------
def get_sid():
    user = session.get("user","guest")

    if "sid" not in session:
        sid = str(uuid.uuid4())
        session["sid"] = sid
        SESSION_STORE[sid] = []
        USERS.setdefault(user, []).append(sid)

    return session["sid"]

# ---------------- MEMORY ----------------
def update_case_memory(sid, text):
    if sid not in CASE_MEMORY:
        CASE_MEMORY[sid] = {"facts": {}}

    f = CASE_MEMORY[sid]["facts"]
    t = text.lower()

    if "usb" in t: f["connection"] = "USB"
    if "wifi" in t: f["connection"] = "WiFi"
    if "windows 11" in t: f["os"] = "Windows 11"
    if "ready" in t: f["printer"] = "Ready"
    if "recognized" in t: f["recognized"] = "Yes"
    if "not print" in t or "doesn't print" in t:
        f["issue"] = "Print failure"
        ANALYTICS["issues"]["print_failure"] = ANALYTICS["issues"].get("print_failure",0)+1

# ---------------- FIX MODE ----------------
def fix_mode(facts):
    return len(facts) >= 4

# ---------------- SAFE COMMANDS ----------------
def run_fix_command(fix):
    if platform.system() != "Windows":
        return "Fix execution only supported on Windows"

    try:
        if "spooler" in fix.lower():
            subprocess.run(["net","stop","spooler"], shell=True)
            subprocess.run(["net","start","spooler"], shell=True)
            ANALYTICS["fixes_run"] += 1
            return "Print Spooler restarted"

        return "No automation mapped for this fix yet"

    except Exception as e:
        return str(e)

# ---------------- AI ----------------
def ask_ai(messages):
    res = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        temperature=0.3
    )
    return res.choices[0].message.content

# ---------------- ROUTES ----------------
@app.route("/dashboard")
def dashboard():
    if "user" not in session:
        return redirect("/")
    return render_template("dashboard.html")

@app.route("/chat", methods=["POST"])
def chat():
    sid = get_sid()
    text = request.json.get("message")

    update_case_memory(sid, text)
    facts = CASE_MEMORY[sid]["facts"]

    if sid not in CHAT_MEMORY:
        CHAT_MEMORY[sid] = []

    history = CHAT_MEMORY[sid]

    mode = fix_mode(facts)

    system = "Only give Fix: solutions" if mode else "Ask one question only"

    messages = [{"role":"system","content":system}]
    messages.append({"role":"system","content":f"FACTS: {facts}"})

    for m in history[-10:]:
        messages.append(m)

    messages.append({"role":"user","content":text})

    reply = ask_ai(messages)

    history.append({"role":"user","content":text})
    history.append({"role":"assistant","content":reply})

    SESSION_STORE[sid] = history

    return jsonify({
        "response": reply,
        "facts": facts,
        "fix_mode": mode,
        "sessions": USERS.get(session["user"],[]),
        "analytics": ANALYTICS
    })

@app.route("/run_fix", methods=["POST"])
def run_fix():
    fix = request.json.get("fix")
    result = run_fix_command(fix)
    return jsonify({"result": result})

@app.route("/load_session", methods=["POST"])
def load_session():
    sid = request.json.get("sid")
    return jsonify(SESSION_STORE.get(sid, []))

# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run(debug=True)
