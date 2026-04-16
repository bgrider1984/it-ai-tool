<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>IT Copilot</title>

<style>
body {
    margin: 0;
    font-family: Arial;
    background: #0f172a;
    color: white;
}

.container {
    max-width: 900px;
    margin: auto;
    padding: 20px;
}

h2 {
    text-align: center;
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
    padding: 10px;
    margin: 6px 0;
    border-radius: 10px;
    max-width: 70%;
    white-space: pre-wrap;
}

.user {
    background: #2563eb;
    align-self: flex-end;
}

.bot {
    background: #374151;
    align-self: flex-start;
}

/* ACTION BUTTONS */
.actions {
    margin-top: 5px;
    display: flex;
    gap: 8px;
    flex-wrap: wrap;
}

.actionBtn {
    background: #22c55e;
    border: none;
    padding: 6px 10px;
    border-radius: 6px;
    cursor: pointer;
    font-size: 12px;
}

.actionBtn:hover {
    background: #16a34a;
}

.inputArea {
    display: flex;
    gap: 10px;
    margin-top: 10px;
}

input {
    flex: 1;
    padding: 12px;
    border-radius: 8px;
    border: none;
}

button {
    padding: 12px 16px;
    border: none;
    background: #22c55e;
    border-radius: 8px;
    cursor: pointer;
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

let sessionId = null;

const chat = document.getElementById("chat");
const input = document.getElementById("input");

input.addEventListener("keydown", function(e){
    if(e.key === "Enter"){
        e.preventDefault();
        send();
    }
});

// ----------------------------
// CHAT MESSAGE
// ----------------------------
function addMessage(text, type){
    const div = document.createElement("div");
    div.className = "msg " + type;
    div.textContent = text;
    chat.appendChild(div);
    chat.scrollTop = chat.scrollHeight;
}

// ----------------------------
// ACTION RUNNER (GUIDED STEPS)
// ----------------------------
async function runAction(actionId){
    let step = 0;

    async function next(){
        const res = await fetch("/action", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({
                action_id: actionId,
                step: step
            })
        });

        const data = await res.json();

        if(data.done){
            addMessage(data.message, "bot");
            return;
        }

        addMessage(data.instruction, "bot");
        step = data.next_step;
    }

    next();
}

// ----------------------------
// SEND MESSAGE
// ----------------------------
async function send(){

    const msg = input.value.trim();
    if(!msg) return;

    addMessage(msg, "user");
    input.value = "";

    const res = await fetch("/ask", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({
            message: msg,
            session_id: sessionId
        })
    });

    const data = await res.json();

    sessionId = data.session_id;

    addMessage(data.response, "bot");

    // render actions
    if(data.actions && data.actions.length > 0){
        const wrap = document.createElement("div");
        wrap.className = "actions";

        data.actions.forEach(a => {
            const btn = document.createElement("button");
            btn.className = "actionBtn";
            btn.innerText = a.label;

            btn.onclick = () => runAction(a.id);

            wrap.appendChild(btn);
        });

        chat.appendChild(wrap);
        chat.scrollTop = chat.scrollHeight;
    }
}

</script>

</body>
</html>
