from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from HabitHive import AuthManager
import os
import firebase_admin
from firebase_admin import auth, credentials, firestore
import json

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'your-secret-key-change-this-in-production')

# Initialize Firebase Admin SDK
try:
    # Check if Firebase app is already initialized
    try:
        firebase_admin.get_app()
        print("Firebase Admin SDK already initialized")
    except ValueError:
        # App doesn't exist, initialize it
        cred = credentials.Certificate('firebase-credentials.json')
        firebase_admin.initialize_app(cred, 
                                      {
        "storageBucket": "kappa-36c9a.appspot.com"  
    })
        print("Firebase Admin SDK initialized successfully")
except Exception as e:
    print(f"Firebase Admin SDK initialization failed: {e}")


# Clients
db = firestore.client()
bucket = storage.bucket()

# -------------------------------------------------------
# Helper: Generate signed URL for secure downloads
# -------------------------------------------------------
def generate_signed_url(blob_path, expiration_minutes=1440):
    blob = bucket.blob(blob_path)
    url = blob.generate_signed_url(
        version="v4",
        expiration=timedelta(minutes=expiration_minutes),
        method="GET",
    )
    return url

@app.route('/')
def index():
    """Home page - redirect based on authentication status"""
    if 'user_email' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login page"""
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        
        if not email or not password:
            flash('Please fill in all fields', 'error')
            return render_template('login.html')
        
        success, message = AuthManager.login(email, password)
        
        if success:
            session['user_email'] = email
            flash(message, 'success')
            return redirect(url_for('dashboard'))
        else:
            flash(message, 'error')
            return render_template('login.html')
    
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    """Signup page"""
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        
        if not email or not password or not confirm_password:
            flash('Please fill in all fields', 'error')
            return render_template('signup.html')
        
        if password != confirm_password:
            flash('Passwords do not match', 'error')
            return render_template('signup.html')
        
        success, message = AuthManager.sign_up(email, password)
        
        if success:
            flash('Account created successfully! Please log in.', 'success')
            return redirect(url_for('login'))
        else:
            flash(message, 'error')
    
    return render_template('signup.html')

@app.route('/dashboard')
def dashboard():
    """Dashboard page - requires authentication"""
    if 'user_email' not in session:
        flash('Please log in to access the dashboard', 'error')
        return redirect(url_for('login'))
    
    user_email = session['user_email']
    return render_template('dashboard.html', user_email=user_email)

# -------------------------------------------------------
# PROFILE CREATION
# -------------------------------------------------------

@app.route("/create-profile", methods=["GET", "POST"])
def create_profile():
    """Create new user profile"""
    if "user_email" not in session:
        flash("Please log in first.", "error")
        return redirect(url_for("login"))

    email = session["user_email"]
    uid = session["user_uid"]

    if request.method == "POST":
        first_name = request.form.get("first_name", "").strip()
        last_name = request.form.get("last_name", "").strip()
        display_name = request.form.get("display_name", "").strip()
        avatar_file = request.files.get("avatar")

        if not first_name or not last_name:
            flash("First and last name are required.", "error")
            return render_template("create_profile.html")

        avatar_url = None
        if avatar_file and avatar_file.filename:
            filename = secure_filename(f"{uid}_avatar.png")
            blob_path = f"users/avatars/{uid}/{filename}"
            blob = bucket.blob(blob_path)
            blob.upload_from_file(avatar_file)
            blob.content_type = "image/png"
            blob.patch()
            avatar_url = generate_signed_url(blob_path)

        profile_data = {
            "email": email,
            "uid": uid,
            "first_name": first_name,
            "last_name": last_name,
            "display_name": display_name or f"{first_name} {last_name}",
            "avatar_path": f"users/avatars/{uid}/{uid}_avatar.png" if avatar_file else None,
            "avatar_url": avatar_url or "https://via.placeholder.com/150",
        }

        db.collection("profiles").document(email).set(profile_data)
        flash("Profile created successfully!", "success")
        return redirect(url_for("profile"))

    return render_template("create_profile.html")


# -------------------------------------------------------
# PROFILE VIEW
# -------------------------------------------------------

@app.route("/profile")
def profile():
    """View existing profile"""
    if "user_email" not in session:
        flash("Please log in to view your profile", "error")
        return redirect(url_for("login"))

    email = session["user_email"]
    doc_ref = db.collection("profiles").document(email)
    doc = doc_ref.get()

    if not doc.exists:
        flash("Profile not found. Please create one.", "info")
        return redirect(url_for("create_profile"))

    profile = doc.to_dict()

    # Refresh signed URL
    if profile.get("avatar_path"):
        profile["avatar_url"] = generate_signed_url(profile["avatar_path"])

    return render_template("profile.html", profile=profile)


# -------------------------------------------------------
# PROFILE EDIT
# -------------------------------------------------------

@app.route("/edit-profile", methods=["GET", "POST"])
def edit_profile():
    """Edit existing profile"""
    if "user_email" not in session:
        flash("Please log in to edit your profile", "error")
        return redirect(url_for("login"))

    email = session["user_email"]
    uid = session["user_uid"]

    doc_ref = db.collection("profiles").document(email)
    doc = doc_ref.get()

    if not doc.exists:
        flash("Profile not found. Please create one.", "info")
        return redirect(url_for("create_profile"))

    profile = doc.to_dict()

    if request.method == "POST":
        first_name = request.form.get("first_name", "").strip()
        last_name = request.form.get("last_name", "").strip()
        display_name = request.form.get("display_name", "").strip()
        avatar_file = request.files.get("avatar")

        avatar_path = profile.get("avatar_path")
        avatar_url = profile.get("avatar_url")

        if avatar_file and avatar_file.filename:
            filename = secure_filename(f"{uid}_avatar.png")
            blob_path = f"users/avatars/{uid}/{filename}"
            blob = bucket.blob(blob_path)
            blob.upload_from_file(avatar_file)
            blob.content_type = "image/png"
            blob.patch()
            avatar_path = blob_path
            avatar_url = generate_signed_url(blob_path)

        updated_data = {
            "first_name": first_name or profile.get("first_name"),
            "last_name": last_name or profile.get("last_name"),
            "display_name": display_name or profile.get("display_name"),
            "avatar_path": avatar_path,
            "avatar_url": avatar_url,
        }

        doc_ref.update(updated_data)
        flash("Profile updated successfully!", "success")
        return redirect(url_for("profile"))

    return render_template("edit_profile.html", profile=profile)


@app.route('/verify-token', methods=['POST'])
def verify_token():
    """Verify Firebase ID token and create session"""
    try:
        data = request.get_json()
        if not data or 'idToken' not in data:
            return jsonify({'error': 'No ID token provided'}), 400
        
        # Verify the ID token
        decoded_token = auth.verify_id_token(data['idToken'])
        user_email = decoded_token['email']
        user_uid = decoded_token['uid']
        
        # Create session
        session['user_email'] = user_email
        session['user_uid'] = user_uid
        
        return jsonify({
            'success': True,
            'email': user_email,
            'uid': user_uid
        }), 200
        
    except Exception as e:
        print(f"Token verification error: {e}")
        return jsonify({'error': 'Invalid token'}), 401

@app.route('/logout')
def logout():
    """Logout page - triggers Firebase signout and clears session"""
    session.clear()
    return render_template('logout.html')

@app.route('/firebase-debug')
def firebase_debug():
    """Firebase debugging page"""
    return render_template('firebase_debug.html')

if __name__ == '__main__':
    app.run(debug=True, host='127.0.0.1', port=5000)
