from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from HabitHive import AuthManager
import os
import firebase_admin
from firebase_admin import auth, credentials, firestore, storage
import json
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
        return redirect(url_for("login"))
    return render_template("dashboard.html", user_email=session['user_email'])

# -------------------------------------------------------
# ✅ PROFILE — CREATE
# -------------------------------------------------------
@app.route('/create-profile', methods=['GET','POST'])
def create_profile():
    if "user_email" not in session:
        return redirect(url_for("login"))

    email = session['user_email']
    uid = session['user_uid']

    if request.method == "POST":
        first = request.form.get("first_name","").strip()
        last = request.form.get("last_name","").strip()
        display = request.form.get("display_name","").strip()
        avatar_file = request.files.get("avatar")

        if not first or not last:
            flash("First and last name are required.", "error")
            return render_template("create_profile.html")

        avatar_path = None
        avatar_url = None

        if avatar_file and avatar_file.filename:
            filename = secure_filename(f"{uid}_avatar.png")
            avatar_path = f"users/avatars/{uid}/{filename}"
            blob = bucket.blob(avatar_path)
            blob.upload_from_file(avatar_file)
            blob.content_type = "image/png"
            blob.patch()
            avatar_url = generate_signed_url(avatar_path)
        else:
            avatar_url = "https://via.placeholder.com/150"

        profile_data = {
            "uid": uid,
            "email": email,
            "first_name": first,
            "last_name": last,
            "display_name": display or f"{first} {last}",
            "avatar_path": avatar_path,
            "avatar_url": avatar_url
        }

        db.collection("profiles").document(email).set(profile_data)
        flash("Profile created successfully!", "success")
        return redirect(url_for("profile"))

    return render_template("create_profile.html")

# -------------------------------------------------------
# ✅ PROFILE — VIEW
# -------------------------------------------------------
@app.route('/profile')
def profile():
    if "user_email" not in session:
        return redirect(url_for("login"))

    email = session["user_email"]
    doc = db.collection("profiles").document(email).get()

    if not doc.exists:
        flash("Please create a profile first.", "info")
        return redirect(url_for("create_profile"))

    profile = doc.to_dict()

    if profile.get("avatar_path"):
        profile["avatar_url"] = generate_signed_url(profile["avatar_path"])

    return render_template("profile.html", profile=profile)

# -------------------------------------------------------
# ✅ PROFILE — EDIT
# -------------------------------------------------------
@app.route('/edit-profile', methods=['GET','POST'])
def edit_profile():
    if "user_email" not in session:
        return redirect(url_for("login"))

    email = session["user_email"]
    uid = session["user_uid"]

    doc_ref = db.collection("profiles").document(email)
    doc = doc_ref.get()

    if not doc.exists:
        return redirect(url_for("create_profile"))

    profile = doc.to_dict()

    if request.method == "POST":
        first = request.form.get("first_name")
        last = request.form.get("last_name")
        display = request.form.get("display_name")
        avatar_file = request.files.get("avatar")

        avatar_path = profile.get("avatar_path")
        avatar_url = profile.get("avatar_url")

        if avatar_file and avatar_file.filename:
            filename = secure_filename(f"{uid}_avatar.png")
            avatar_path = f"users/avatars/{uid}/{filename}"
            blob = bucket.blob(avatar_path)
            blob.upload_from_file(avatar_file)
            blob.content_type = "image/png"
            blob.patch()
            avatar_url = generate_signed_url(avatar_path)

        updated = {
            "first_name": first or profile["first_name"],
            "last_name": last or profile["last_name"],
            "display_name": display or profile["display_name"],
            "avatar_path": avatar_path,
            "avatar_url": avatar_url
        }

        doc_ref.update(updated)
        flash("Profile updated!", "success")
        return redirect(url_for("profile"))

    return render_template("edit_profile.html", profile=profile)

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

# -------------------------------------------------------
# ✅ RUN APP
# -------------------------------------------------------
if __name__ == '__main__':
    app.run(debug=True, host="127.0.0.1", port=5000)
