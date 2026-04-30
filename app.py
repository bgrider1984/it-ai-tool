@app.route("/api/run", methods=["POST"])
def run():
    try:
        cid = get_cid()
        case = load_case(cid)

        text = request.json.get("text", "")

        result = run_agent(text, case)

        case["history"].append({
            "type": "step",
            "input": text,
            "response": result.get("analysis")
        })

        save_case(cid, case)

        return safe_response(result)

    except Exception as e:
        return safe_response(error=str(e))
