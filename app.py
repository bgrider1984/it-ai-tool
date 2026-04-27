from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from openai import OpenAI
import os, uuid

app = Flask(__name__)
app.secret_key = "dev-secret"

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
MODEL = "gpt-4.1-mini"

CHAT_MEMORY = {}
CASE_MEMORY = {}
SESSION_STORE = {}

# ---------------- AUTH ----------------
@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        session["user"] = username
        return redirect("/dashboard")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

# ---------------- SESSION ----------------
def get_sid():
    if "sid" not in session:
        sid = str(uuid.uuid4())
        session["sid"] = sid
        SESSION_STORE[sid] = []
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
    if "print" in t and "not" in t: f["issue"] = "Print failure"

def fix_mode(facts):
    return len(facts) >= 4

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
    facts = CASE_MEMORY.get(sid, {}).get("facts", {})

    if sid not in CHAT_MEMORY:
        CHAT_MEMORY[sid] = []

    history = CHAT_MEMORY[sid]

    mode = fix_mode(facts)

    system = """
    FIX MODE: Only give solutions. Each must start with Fix:
    """ if mode else """
    Ask one question. Do not repeat.
    """

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
        "sessions": list(SESSION_STORE.keys())
    })

@app.route("/load_session", methods=["POST"])
def load_session():
    sid = request.json.get("sid")
    data = SESSION_STORE.get(sid, [])
    return jsonify(data)

# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run(debug=True)
