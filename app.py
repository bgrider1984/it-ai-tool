@app.route("/ask", methods=["POST"])
def ask():
    msg = request.json.get("message","").strip()

    user = get_user()

    session = get_session(user)

    # store user message
    session["messages"].append({"role":"user","text":msg})

    route = session["state"]["route"]
    step = session["state"]["step"]

    if not route:
        route = classify_issue(msg)
        session["state"]["route"] = route

    result = route_step(route, step, msg)

    if "step" in result:
        session["state"]["step"] = result["step"]

    session["messages"].append({
        "role":"bot",
        "text":result["text"]
    })

    return jsonify({
        "response": result["text"],
        "sessions": list(user["sessions"].values())
    })
