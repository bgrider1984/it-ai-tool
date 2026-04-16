<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>IT Copilot</title>

<style>
body {
    margin: 0;
    font-family: Arial;
    background: #0b1220;
    color: white;
}

.container {
    max-width: 900px;
    margin: auto;
    padding: 20px;
}

#chat {
    height: 70vh;
    overflow-y: auto;
    background: #111827;
    padding: 15px;
    border-radius: 10px;
    display: flex;
    flex-direction: column;
}

.msg {
    margin: 6px 0;
    padding: 10px;
    border-radius: 10px;
    max-width: 70%;
}

.user {
    background: #2563eb;
    align-self: flex-end;
}

.bot {
    background: #374151;
    align-self: flex-start;
}

.fix-btn {
    margin-top: 6px;
    margin-right: 6px;
    padding: 6px 10px;
    border-radius: 6px;
    border: none;
    cursor: pointer;
}

.high { background: #22c55e; }
.medium { background: #eab308; }
.low { background: #ef4444; }

.inputArea {
    display: flex;
    gap: 10px;
    margin-top: 10px;
}

input {
    flex: 1;
    padding: 10px;
    border-radius: 8px;
    border: none;
}

button {
    padding: 10px;
    border-radius: 8px;
    border: none;
    background: #22c55e;
}
</style>
</head>

<body>

<div class="container">
<h2>IT Copilot</h2>

<div id="chat"></div>

<div class="inputArea">
    <input id="input" placeholder="Describe your issue..." />
    <button onclick="send()">Send</button>
</div>
</div>

<script>

let sessionId = localStorage.getItem("sessionId");
const chat = document.getElementById("chat");
const input = document.getElementById("input");

input.addEventListener("keydown", e => {
    if(e.key === "Enter") send();
});

function add(text, type, fixes=[]){
    const div = document.createElement("div");
    div.className = "msg " + type;
    div.textContent = text;

    // ADD MULTIPLE FIX BUTTONS
    fixes.forEach(fix => {
        const btn = document.createElement("button");
        btn.className = "fix-btn " + fix.confidence.toLowerCase();
        btn.textContent = `${fix.label} (${fix.confidence})`;

        btn.onclick = () => runFix(fix.name);

        div.appendChild(document.createElement("br"));
        div.appendChild(btn);
    });

    chat.appendChild(div);
    chat.scrollTop = chat.scrollHeight;
}

async function runFix(fix){
    add("Running: " + fix, "user");

    const res = await fetch("/ask", {
        method:"POST",
        headers:{"Content-Type":"application/json"},
        body:JSON.stringify({
            run_fix: fix,
            session_id: sessionId
        })
    });

    const data = await res.json();
    add(data.response, "bot");
}

async function send(){
    const msg = input.value.trim();
    if(!msg) return;

    add(msg, "user");
    input.value = "";

    const res = await fetch("/ask", {
        method:"POST",
        headers:{"Content-Type":"application/json"},
        body:JSON.stringify({
            message: msg,
            session_id: sessionId
        })
    });

    const data = await res.json();

    sessionId = data.session_id;
    localStorage.setItem("sessionId", sessionId);

    add(data.response, "bot", data.fixes);
}

</script>

</body>
</html>
