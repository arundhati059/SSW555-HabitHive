from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from HabitHive import AuthManager
import os
import firebase_admin
from firebase_admin import auth, credentials
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
        # Use the kappa-36c9a project credentials
        cred = credentials.Certificate('firebase-credentials.json')
        firebase_admin.initialize_app(cred, {
        'projectId': 'kappa-36c9a'    
    })
        print("Firebase Admin SDK initialized successfully")
except Exception as e:
    print(f"Firebase Admin SDK initialization failed: {e}")
    print("Make sure firebase-credentials.json contains credentials for kappa-36c9a project")

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

@app.route('/verify-token', methods=['POST'])
def verify_token():
    """Verify Firebase ID token and create session"""
    try:
        data = request.get_json()
        if not data or 'idToken' not in data:
            print("No ID token provided in request")
            return jsonify({'error': 'No ID token provided'}), 400
        
        # Verify the ID token
        decoded_token = auth.verify_id_token(data['idToken'])
        user_email = decoded_token['email']
        user_uid = decoded_token['uid']
        
        print(f"Token verified successfully for user: {user_email}")
        
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
        print(f"Error type: {type(e)}")
        return jsonify({'error': f'Token verification failed: {str(e)}'}), 401

@app.route('/logout')
def logout():
    """Logout page - triggers Firebase signout and clears session"""
    session.clear()
    return render_template('logout.html')

@app.route('/firebase-debug')
def firebase_debug():
    """Firebase debugging page"""
    return render_template('firebase_debug.html')
# --- JOURNAL PAGE ---
@app.route('/journal')
def journal_page():
    if 'user_email' not in session:
        return redirect(url_for('login'))
    return render_template('journal.html',
                           user_email=session['user_email'],
                           active_tab='journal')

# Let templates use url_for('journal')
app.view_functions['journal'] = app.view_functions['journal_page']

# --- JOURNAL API ---
@app.route('/api/journals', methods=['GET', 'POST'])
def journals_api():
    if 'user_email' not in session:
        return jsonify({'success': False, 'error': 'Authentication required'}), 401
    if not db:
        return jsonify({'success': False, 'error': 'Database unavailable'}), 500

    user_id = session.get('user_uid', session['user_email'])

    # CREATE
    if request.method == 'POST':
        payload = request.get_json() or {}
        title = (payload.get('title') or '').strip()
        content = (payload.get('content') or '').strip()
        mood = (payload.get('mood') or '🙂').strip()
        if not title or not content:
            return jsonify({'success': False, 'error': 'Title and content are required'}), 400
        doc = {
            'userID': user_id,
            'title': title,
            'content': content,
            'mood': mood,
            'createdAt': datetime.now()
        }
        ref = db.collection('journals').document()
        ref.set(doc)
        return jsonify({'success': True, 'id': ref.id}), 200

    # LIST (newest first)
    query = (db.collection('journals')
             .where('userID', '==', user_id)
             .order_by('createdAt', direction=firestore.Query.DESCENDING)
             .limit(25))
    snaps = query.stream()
    entries = []
    for s in snaps:
        d = s.to_dict() or {}
        if isinstance(d.get('createdAt'), datetime):
            d['createdAt'] = d['createdAt'].isoformat()
        elif hasattr(d.get('createdAt'), 'to_datetime'):
            try: d['createdAt'] = d['createdAt'].to_datetime().isoformat()
            except: pass
        d['id'] = s.id
        entries.append(d)
    return jsonify({'success': True, 'entries': entries}), 200

@app.route('/api/journals/<doc_id>', methods=['DELETE'])
def journals_delete(doc_id):
    if 'user_email' not in session:
        return jsonify({'success': False, 'error': 'Authentication required'}), 401
    if not db:
        return jsonify({'success': False, 'error': 'Database unavailable'}), 500

    user_id = session.get('user_uid', session['user_email'])
    ref = db.collection('journals').document(doc_id)
    snap = ref.get()
    if not snap.exists:
        return jsonify({'success': False, 'error': 'Not found'}), 404
    data = snap.to_dict() or {}
    if data.get('userID') != user_id:
        return jsonify({'success': False, 'error': 'Forbidden'}), 403
    ref.delete()
    return jsonify({'success': True}), 200
# --- PROFILE: CREATE / VIEW ---
@app.route('/create-profile', methods=['GET','POST'])
def create_profile():
    if "user_email" not in session:
        return redirect(url_for("login"))

    email = session['user_email']
    uid = session.get('user_uid', email.replace('@','_').replace('.','_'))

    if request.method == "POST":
        first = request.form.get("first_name","").strip()
        last = request.form.get("last_name","").strip()
        display = request.form.get("display_name","").strip()
        avatar_file = request.files.get("avatar")

        if not first or not last:
            flash("First and last name are required.", "error")
            return render_template("create_profile.html", active_tab="profile")

        avatar_path = None
        avatar_url = "https://via.placeholder.com/150"
        if avatar_file and avatar_file.filename:
            filename = secure_filename(f"{uid}_avatar.png")
            avatar_path = f"users/avatars/{uid}/{filename}"
            blob = bucket.blob(avatar_path)
            blob.upload_from_file(avatar_file)
            blob.content_type = "image/png"
            blob.patch()
            avatar_url = generate_signed_url(avatar_path)

        profile_data = {
            "uid": uid, "email": email,
            "first_name": first, "last_name": last,
            "display_name": display or f"{first} {last}",
            "avatar_path": avatar_path, "avatar_url": avatar_url
        }
        db.collection("profiles").document(email).set(profile_data)
        flash("Profile created successfully!", "success")
        return redirect(url_for("profile"))

    return render_template("create_profile.html", active_tab="profile")

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
    return render_template("profile.html", profile=profile, active_tab="profile")

# Allow url_for('profile_page') if templates use it
app.view_functions['profile_page'] = app.view_functions['profile']
# --- HABITS API ---
@app.route('/api/habits', methods=['GET', 'POST'])
def habits_api():
    if 'user_email' not in session:
        return jsonify({'success': False, 'error': 'Authentication required'}), 401
    if not db:
        return jsonify({'success': False, 'error': 'Database unavailable'}), 500

    user_id = session.get('user_uid', session['user_email'])

    # CREATE
    if request.method == 'POST':
        payload = request.get_json() or {}
        name = (payload.get('name') or '').strip()
        description = (payload.get('description') or '').strip()
        frequency = (payload.get('frequency') or 'daily').strip()
        category = (payload.get('category') or 'general').strip()
        if not name:
            return jsonify({'success': False, 'error': 'Habit name is required'}), 400

        doc = {
            'userID': user_id,
            'name': name,
            'description': description,
            'frequency': frequency,
            'category': category,
            'isActive': True,
            'createdAt': datetime.now(),
            'streak': 0
        }
        ref = db.collection('habits').document()
        ref.set(doc)
        return jsonify({'success': True, 'id': ref.id}), 200

    # LIST (newest first)
    query = (db.collection('habits')
             .where('userID', '==', user_id)
             .order_by('createdAt', direction=firestore.Query.DESCENDING))
    snaps = query.stream()
    habits = []
    for s in snaps:
        d = s.to_dict() or {}
        if hasattr(d.get('createdAt'), 'isoformat'):
            d['createdAt'] = d['createdAt'].isoformat()
        d['id'] = s.id
        habits.append(d)
    return jsonify({'success': True, 'habits': habits}), 200

@app.route('/api/habits/<habit_id>', methods=['DELETE'])
def delete_habit(habit_id):
    if 'user_email' not in session:
        return jsonify({'success': False, 'error': 'Authentication required'}), 401
    if not db:
        return jsonify({'success': False, 'error': 'Database unavailable'}), 500

    user_id = session.get('user_uid', session['user_email'])
    ref = db.collection('habits').document(habit_id)
    snap = ref.get()
    if not snap.exists:
        return jsonify({'success': False, 'error': 'Not found'}), 404
    data = snap.to_dict() or {}
    if data.get('userID') != user_id:
        return jsonify({'success': False, 'error': 'Forbidden'}), 403
    ref.delete()
    return jsonify({'success': True}), 200
    
    

if __name__ == '__main__':
    app.run(debug=True, host='127.0.0.1', port=5000)
