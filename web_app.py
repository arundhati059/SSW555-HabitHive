from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from HabitHive import AuthManager
import os
import firebase_admin
from firebase_admin import auth, credentials, firestore, storage
import json
from create_habit import HabitManager
from datetime import datetime, timedelta
import threading
import time
import requests
import uuid
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'your-secret-key-change-this-in-production')

# -------------------------------------------------------
# ✅ FIREBASE INITIALIZATION
# -------------------------------------------------------
try:
    try:
        firebase_admin.get_app()
        print("✅ Firebase Admin SDK already initialized")
    except ValueError:
        cred = credentials.Certificate("firebase-credentials.json")
        firebase_admin.initialize_app(cred, {
            "storageBucket": "kappa-36c9a.appspot.com"
        })
        print("✅ Firebase Admin SDK initialized")
except Exception as e:
    print(f"❌ Firebase initialization failed: {e}")

# Firestore & Bucket Clients
db = firestore.client()
bucket = storage.bucket()

# -------------------------------------------------------
# ✅ Storage Signed URL Helper
# -------------------------------------------------------
def generate_signed_url(blob_path, minutes=1440):
    blob = bucket.blob(blob_path)
    url = blob.generate_signed_url(
        version="v4",
        expiration=timedelta(minutes=minutes),
        method="GET",
    )
    return url

# -------------------------------------------------------
# ✅ AUTH HELPERS
# -------------------------------------------------------
def require_auth():
    if 'user_email' not in session:
        flash("Please log in to continue.", "error")
        return None
    return session["user_email"], session.get("user_uid")

# -------------------------------------------------------
# ✅ BASIC ROUTES
# -------------------------------------------------------
@app.route('/')
def index():
    return redirect(url_for('dashboard') if 'user_email' in session else 'login')

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        email = request.form.get("email","").strip()
        password = request.form.get("password","")

        if not email or not password:
            flash("Please fill all fields", "error")
            return render_template("login.html")

        success, message = AuthManager.login(email, password)
        if success:
            session["user_email"] = email
            session["user_uid"] = email.replace("@","_").replace(".","_")
            return redirect(url_for("dashboard"))
        flash(message, "error")
    return render_template("login.html")

@app.route('/signup', methods=['GET','POST'])
def signup():
    if request.method == 'POST':
        email = request.form.get("email","")
        pwd = request.form.get("password","")
        confirm = request.form.get("confirm_password","")

        if not email or not pwd or not confirm:
            flash("Fill all fields", "error")
            return render_template("signup.html")

        if pwd != confirm:
            flash("Passwords do not match", "error")
            return render_template("signup.html")

        success, msg = AuthManager.sign_up(email, pwd)
        if success:
            flash("Account created! Please log in.", "success")
            return redirect(url_for("login"))
        flash(msg, "error")

    return render_template("signup.html")

@app.route('/dashboard')
def dashboard():
    if 'user_email' not in session:
        flash('Please log in to access the dashboard', 'error')
        return redirect(url_for('login'))
    
    user_email = session['user_email']
    return render_template('dashboard.html', user_email=user_email,authenticated=True)

# -------------------------------------------------------
# ✅ FIREBASE TOKEN VERIFICATION
# -------------------------------------------------------
@app.route('/verify-token', methods=['POST'])
def verify_token():
    try:
        data = request.get_json()
        decoded = auth.verify_id_token(data["idToken"])
        session["user_email"] = decoded["email"]
        session["user_uid"] = decoded["uid"]
        return jsonify({"success": True})
    except:
        return jsonify({"error": "Invalid token"}), 401

# -------------------------------------------------------
# ✅ LOGOUT
# -------------------------------------------------------
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for("login"))

# -------------------------------------------------------
# ✅ TESTING ENDPOINTS
# -------------------------------------------------------
@app.route('/firebase-debug')
def firebase_debug():
    return jsonify({"status": "Firebase OK", "session": dict(session)})

@app.route('/habits/create', methods=['POST'])
def create_habit():
    """Create a new habit - no authentication needed"""
    data = request.get_json()
    
    success, message = HabitManager.create_habit(
        habit_name=data.get('name'),
        description=data.get('description', ''),
        frequency=data.get('frequency', 'daily'),
        target_count=data.get('target_count', 1),
        category=data.get('category', 'General')
    )
    
    if success:
        return jsonify({'success': True, 'message': message}), 200
    else:
        return jsonify({'success': False, 'error': message}), 400

@app.route('/habits', methods=['GET'])
def get_habits():
    """Get all habits"""
    habits = HabitManager.get_all_habits()
    return jsonify({'success': True, 'habits': habits}), 200

@app.route('/habits/<habit_name>/complete', methods=['POST'])
def complete_habit(habit_name):
    """Mark habit as complete"""
    success, message = HabitManager.complete_habit(habit_name)
    
    if success:
        return jsonify({'success': True, 'message': message}), 200
    else:
        return jsonify({'success': False, 'error': message}), 400

@app.route('/habits/<habit_name>/uncomplete', methods=['POST'])
def uncomplete_habit(habit_name):
    """Remove today from completion history"""
    # REMOVED: Authentication check - now works without login
    from datetime import datetime
    habits = HabitManager.get_all_habits(active_only=False)
    today = datetime.now().date().isoformat()
    
    for habit in habits:
        if habit['name'].lower() == habit_name.lower():
            if 'completion_history' in habit and today in habit['completion_history']:
                habit['completion_history'].remove(today)
                habit['streak'] = HabitManager._calculate_streak(habit['completion_history'])
                all_habits = HabitManager._load_habits()
                for h in all_habits:
                    if h['name'] == habit['name']:
                        h['completion_history'] = habit['completion_history']
                        h['streak'] = habit['streak']
                HabitManager._save_habits(all_habits)
                return jsonify({'success': True, 'message': 'Unmarked successfully'}), 200
    
    return jsonify({'success': False, 'error': 'Habit not found'}), 404

@app.route('/habits/<habit_name>/delete', methods=['POST'])
def delete_habit_route(habit_name):
    """Delete a habit"""
    success, message = HabitManager.delete_habit(habit_name)
    
    if success:
        return jsonify({'success': True, 'message': message}), 200
    else:
        return jsonify({'success': False, 'error': message}), 400

@app.route('/habits/<habit_name>/update', methods=['POST'])
def update_habit_route(habit_name):
    """Update habit details"""
    data = request.get_json()
    habits = HabitManager._load_habits()
    
    for habit in habits:
        if habit['name'].lower() == habit_name.lower():
            if 'description' in data:
                habit['description'] = data['description']
            
            if 'category' in data:
                habit['category'] = data['category']
            
            if 'privacy' in data:  # Add privacy update
                habit['privacy'] = data['privacy']
            
            HabitManager._save_habits(habits)
            return jsonify({'success': True, 'message': 'Habit updated successfully'}), 200
    
    return jsonify({'success': False, 'error': 'Habit not found'}), 404





# -------------------------------------------------------
# ✅ RUN APP
# -------------------------------------------------------
if __name__ == '__main__':
    app.run(debug=True, host="127.0.0.1", port=5000)
