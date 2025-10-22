import webview
from flask import Flask, jsonify, request, render_template
import threading

# ---------------- Flask Backend ---------------- #
app = Flask(__name__)

# In-memory habit storage for now
habits = [
    {"id": 1, "name": "Drink water", "completed": False},
    {"id": 2, "name": "Exercise", "completed": False}
]

# Replace your get_habits route for the frontend
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/habits/<int:habit_id>/toggle", methods=["POST"])
def toggle_habit(habit_id):
    for habit in habits:
        if habit["id"] == habit_id:
            habit["completed"] = not habit["completed"]
            return jsonify(habit)
    return jsonify({"error": "Habit not found"}), 404

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
