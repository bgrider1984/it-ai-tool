@app.route("/signup", methods=["POST"])
def signup():

    data = request.json or {}
    email = data.get("email", "").strip()
    password = data.get("password", "").strip()

    if not email or not password:
        return jsonify({"error": "Email and password required"}), 400

    existing = User.query.filter_by(email=email).first()
    if existing:
        return jsonify({"error": "User already exists"}), 400

    user = User(email=email, password=password)

    db.session.add(user)
    db.session.commit()

    return jsonify({"status": "created"})


@app.route("/login", methods=["POST"])
def login():

    data = request.json or {}
    email = data.get("email", "").strip()
    password = data.get("password", "").strip()

    if not email or not password:
        return jsonify({"error": "Missing credentials"}), 400

    user = User.query.filter_by(email=email, password=password).first()

    if not user:
        return jsonify({"error": "Invalid login"}), 401

    session["user_id"] = user.id

    return jsonify({"status": "logged_in"})
