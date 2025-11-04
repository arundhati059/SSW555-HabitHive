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

if __name__ == '__main__':
    app.run(debug=True, host='127.0.0.1', port=5000)