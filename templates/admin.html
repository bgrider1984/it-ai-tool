<!DOCTYPE html>
<html>
<head>
<title>Admin Panel</title>

<style>
body {
    font-family: Arial;
    background:#0b1220;
    color:white;
    padding:20px;
}

.box {
    background:#111827;
    padding:15px;
    margin-bottom:15px;
    border-radius:10px;
}

button {
    padding:10px;
    background:#22c55e;
    color:white;
    border:none;
    border-radius:6px;
    cursor:pointer;
}
</style>
</head>

<body>

<h1>🧠 Beta Admin Panel</h1>

<div class="box">
<h3>Generate Invite</h3>
<button onclick="genInvite()">Create Invite Code</button>
<p id="invite"></p>
</div>

<div class="box">
<h3>Users</h3>
<ul>
{% for u in users %}
<li>{{u.email}} | plan: {{u.plan}}</li>
{% endfor %}
</ul>
</div>

<div class="box">
<h3>Feedback</h3>
<ul>
{% for f in feedback %}
<li>{{f.message}} → Helpful: {{f.helpful}}</li>
{% endfor %}
</ul>
</div>

<script>

async function genInvite(){
    const res = await fetch("/admin/generate-invite", {
        method:"POST"
    });

    const data = await res.json();
    document.getElementById("invite").innerText = data.invite;
}

</script>

</body>
</html>
