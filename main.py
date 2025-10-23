import webview
from flask import Flask, jsonify, request, render_template
import threading

# ---------------- Flask Backend ---------------- #
app = Flask(__name__)

# In-memory habit storage for now
habits = [
    {"id": 1, "name": "Drink water", "completed": False, "category": "Health"},
    {"id": 2, "name": "Exercise", "completed": False, "category": "Fitness"}
]

# Replace your get_habits route for the frontend
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/habits", methods=["GET"])
def get_habits():
    return jsonify(habits)


@app.route("/habits/<int:habit_id>/toggle", methods=["POST"])
def toggle_habit(habit_id):
    for habit in habits:
        if habit["id"] == habit_id:
            habit["completed"] = not habit["completed"]
            return jsonify(habit)
    return jsonify({"error": "Habit not found"}), 404

@app.route("/habits", methods=["POST"])
def add_habit():
    data = request.get_json()
    name = data.get("name")
    category = data.get("category", "Uncategorized")  # default if user doesn't provide
    if not name:
        return jsonify({"error": "Habit name is required"}), 400

    new_habit = {
        "id": len(habits) + 1,
        "name": name,
        "completed": False,
        "category": category
    }
    habits.append(new_habit)
    return jsonify(new_habit), 201

@app.route("/habits/category/<string:category_name>", methods=["GET"])
def get_habits_by_category(category_name):
    filtered = [habit for habit in habits if habit["category"].lower() == category_name.lower()]
    return jsonify(filtered)


# ---------------- PyWebView Frontend ---------------- #
def start_flask():
    # Flask runs on localhost:5000
    app.run(debug=False)

if __name__ == "__main__":
    # Run Flask in a separate thread
    threading.Thread(target=start_flask, daemon=True).start()
    
    # Open a pywebview window pointing to Flask app
    webview.create_window("Habit Hive", "http://127.0.0.1:5000")
    webview.start()
