@app.route("/journal", methods=["POST"])
def add_journal_entry():
    data = request.json
    user_id = data.get("user_id")
    entry_text = data.get("entry_text")
    date = datetime.now().strftime("%Y-%m-%d")

    if not user_id or not entry_text:
        return jsonify({"error": "Missing required fields"}), 400
    
    db.collection("journals").add({
        "user_id": user_id,
        "entry_text": entry_text,
        "date": date
    })
    return jsonify({"message": "Journal entry added successfully"}), 200
