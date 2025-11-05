from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from HabitHive import AuthManager
import os
import firebase_admin
from firebase_admin import auth, credentials, firestore
import json
from datetime import datetime
import threading
import time
import requests
import uuid

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
        firebase_admin.initialize_app(cred)
        print("Firebase Admin SDK initialized successfully")
except Exception as e:
    print(f"Firebase Admin SDK initialization failed: {e}")

# Initialize Firestore
try:
    db = firestore.client()
    print("Firestore client initialized successfully")
except Exception as e:
    print(f"Firestore initialization failed: {e}")
    db = None

# Firestore REST API helper function
def firestore_rest_api_create(collection, data):
    """Create document using Firestore REST API as fallback"""
    try:
        # Read project_id from credentials
        with open('firebase-credentials.json', 'r') as f:
            creds = json.load(f)
            project_id = creds['project_id']
        
        # Generate document ID
        doc_id = str(uuid.uuid4())
        
        # Firestore REST API endpoint
        url = f"https://firestore.googleapis.com/v1/projects/{project_id}/databases/(default)/documents/{collection}/{doc_id}"
        
        # Convert Python datetime to Firestore timestamp format
        def convert_datetime(obj):
            if isinstance(obj, datetime):
                return {'timestampValue': obj.isoformat() + 'Z'}
            return obj
        
        # Convert data to Firestore format
        firestore_fields = {}
        for key, value in data.items():
            if isinstance(value, str):
                firestore_fields[key] = {'stringValue': value}
            elif isinstance(value, int):
                firestore_fields[key] = {'integerValue': str(value)}
            elif isinstance(value, datetime):
                firestore_fields[key] = {'timestampValue': value.isoformat() + 'Z'}
            elif isinstance(value, bool):
                firestore_fields[key] = {'booleanValue': value}
        
        payload = {'fields': firestore_fields}
        
        # Make request with timeout
        response = requests.post(url, json=payload, timeout=5)
        
        if response.status_code in [200, 201]:
            print(f"✅ REST API: Document created with ID: {doc_id}")
            return doc_id
        else:
            print(f"❌ REST API error: {response.status_code} - {response.text}")
            return None
            
    except Exception as e:
        print(f"💥 REST API exception: {e}")
        return None

    db = None

@app.route('/login', methods=['GET'])
def login():
    """Login page - Auth handled by Firebase on frontend"""
    return render_template('login.html')

@app.route('/signup', methods=['GET'])
def signup():
    """Signup page - Auth handled by Firebase on frontend"""
    return render_template('signup.html')

def require_auth():
    """Helper function to check authentication"""
    if 'user_email' not in session:
        flash('Please log in to access this page', 'error')
        return redirect(url_for('login'))
    
    user_email = session['user_email']
    user_uid = session.get('user_uid', 'temp_uid_' + user_email.replace('@', '_').replace('.', '_'))
    
    # Store a temporary UID if not available
    if 'user_uid' not in session:
        session['user_uid'] = user_uid
    
    return user_email, user_uid

@app.route('/')
def index():
    """Home page - redirect based on authentication status"""
    if 'user_email' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/dashboard')
def dashboard():
    """Dashboard/Home page - requires authentication"""
    auth_result = require_auth()
    if isinstance(auth_result, type(redirect(url_for('login')))):
        return auth_result
    
    user_email, user_uid = auth_result
    return render_template('dashboard.html', user_email=user_email, user_uid=user_uid, active_tab='home')

@app.route('/create')
def create_page():
    """Create page - goal and habit creation"""
    auth_result = require_auth()
    if isinstance(auth_result, type(redirect(url_for('login')))):
        return auth_result
    
    user_email, user_uid = auth_result
    return render_template('create.html', user_email=user_email, user_uid=user_uid, active_tab='create')

@app.route('/analytics')
def analytics_page():
    """Analytics page - progress tracking and insights - Coming Soon"""
    auth_result = require_auth()
    if isinstance(auth_result, type(redirect(url_for('login')))):
        return auth_result
    
    user_email, user_uid = auth_result
    return render_template('coming_soon.html', 
                         user_email=user_email, 
                         user_uid=user_uid, 
                         active_tab='analytics',
                         page_title='Analytics',
                         page_icon='fas fa-chart-line',
                         features=[
                             'Detailed progress tracking and charts',
                             'Habit completion statistics',
                             'Trend analysis and insights',
                             'Goal achievement metrics',
                             'Custom report generation'
                         ])

@app.route('/friends')
def friends_page():
    """Friends page - social features - Coming Soon"""
    auth_result = require_auth()
    if isinstance(auth_result, type(redirect(url_for('login')))):
        return auth_result
    
    user_email, user_uid = auth_result
    return render_template('coming_soon.html', 
                         user_email=user_email, 
                         user_uid=user_uid, 
                         active_tab='friends',
                         page_title='Friends',
                         page_icon='fas fa-user-friends',
                         features=[
                             'Connect with friends and family',
                             'Share goals and achievements',
                             'Challenge friends to habit competitions',
                             'Group goals and team challenges',
                             'Social motivation and support'
                         ])

@app.route('/explore')
def explore_page():
    """Explore page - discover habits and templates"""
    auth_result = require_auth()
    if isinstance(auth_result, type(redirect(url_for('login')))):
        return auth_result
    
    user_email, user_uid = auth_result
    return render_template('explore.html', user_email=user_email, user_uid=user_uid, active_tab='explore')

@app.route('/meals')
def meals_page():
    """Meals page - nutrition and meal planning - Coming Soon"""
    auth_result = require_auth()
    if isinstance(auth_result, type(redirect(url_for('login')))):
        return auth_result
    
    user_email, user_uid = auth_result
    return render_template('coming_soon.html', 
                         user_email=user_email, 
                         user_uid=user_uid, 
                         active_tab='meals',
                         page_title='Meals',
                         page_icon='fas fa-utensils',
                         features=[
                             'Meal planning and nutrition tracking',
                             'Recipe suggestions and meal prep',
                             'Calorie and macro tracking',
                             'Healthy eating habit formation',
                             'Integration with fitness goals'
                         ])

@app.route('/profile')
def profile_page():
    """Profile page - user settings and preferences"""
    auth_result = require_auth()
    if isinstance(auth_result, type(redirect(url_for('login')))):
        return auth_result
    
    user_email, user_uid = auth_result
    
    # Extract username from email (part before @)
    username = user_email.split('@')[0] if user_email else 'User'
    
    # Get user registration date (you can enhance this to get actual data from Firestore)
    from datetime import datetime
    # For now, using current date - you can replace this with actual registration date from database
    member_since = datetime.now().strftime("%B %Y")
    
    return render_template('profile.html', 
                         user_email=user_email, 
                         user_uid=user_uid, 
                         active_tab='profile',
                         username=username,
                         member_since=member_since)

@app.route('/verify-token', methods=['POST'])
def verify_token():
    """Verify Firebase ID token and create session"""
    print("🔐 VERIFY-TOKEN endpoint hit!")
    try:
        data = request.get_json()
        print(f"🔐 VERIFY-TOKEN called with data: {data}")
        print(f"🔐 Content-Type: {request.content_type}")
        print(f"🔐 Raw data: {request.data}")
        
        if not data or 'idToken' not in data:
            print("❌ No ID token provided")
            return jsonify({'error': 'No ID token provided'}), 400
        
        # Verify the ID token
        print("🔍 Verifying Firebase ID token...")
        print(f"🔍 Token length: {len(data['idToken'])}")
        decoded_token = auth.verify_id_token(data['idToken'])
        user_email = decoded_token['email']
        user_uid = decoded_token['uid']
        
        print(f"✅ Token verified! Email: {user_email}, UID: {user_uid}")
        
        # Create session with real Firebase UID
        session['user_email'] = user_email
        session['user_uid'] = user_uid  # Real Firebase UID, not temp
        
        return jsonify({
            'success': True,
            'email': user_email,
            'uid': user_uid
        }), 200
        
    except Exception as e:
        print(f"💥 Token verification error: {e}")
        print(f"💥 Error type: {type(e)}")
        import traceback
        print(f"💥 Full traceback: {traceback.format_exc()}")
        return jsonify({'error': 'Invalid token'}), 401

@app.route('/logout')
def logout():
    """Logout - clears session and redirects to login"""
    session.clear()
    flash('You have been logged out successfully', 'success')
    return redirect(url_for('login'))

@app.route('/test-backend', methods=['GET', 'POST'])
def test_backend():
    """Test endpoint to verify backend is working"""
    print(f"🧪 TEST-BACKEND called - Method: {request.method}")
    if request.method == 'POST':
        data = request.get_json()
        print(f"🧪 POST data received: {data}")
    return jsonify({'status': 'Backend is working', 'method': request.method}), 200

@app.route('/create-goal', methods=['GET', 'POST'])
def create_goal():
    """Create a new goal - requires authentication"""
    
    print(f"🎯 CREATE-GOAL ENDPOINT CALLED - Method: {request.method}")
    print(f"📍 Client IP: {request.remote_addr}")
    print(f"📋 Headers: {dict(request.headers)}")
    
    # Handle GET requests (direct browser access)
    if request.method == 'GET':
        print("ℹ️  GET request to /create-goal - returning info")
        return jsonify({
            'message': 'This endpoint expects POST requests with JSON data',
            'session_authenticated': 'user_email' in session,
            'user_email': session.get('user_email', 'Not logged in'),
            'expected_method': 'POST',
            'content_type': 'application/json'
        }), 200
    
    # Debug session information
    print(f"🔐 Session data: {dict(session)}")
    print(f"👤 User email in session: {session.get('user_email')}")
    print(f"🆔 User UID in session: {session.get('user_uid')}")
    
    if 'user_email' not in session:
        print("❌ Authentication failed: No user_email in session")
        return jsonify({'error': 'Authentication required. Please log in again.'}), 401
    
    try:
        print("📦 Processing POST request...")
        data = request.get_json()
        print(f"📊 Received goal data: {data}")
        
        # Validate required fields
        if not data.get('title', '').strip():
            print("❌ Validation failed: Missing title")
            return jsonify({'error': 'Goal title is required'}), 400
        
        if not data.get('type'):
            print("❌ Validation failed: Missing type")
            return jsonify({'error': 'Goal type is required'}), 400
        
        if not data.get('targetDate'):
            print("❌ Validation failed: Missing target date")
            return jsonify({'error': 'Target date is required'}), 400
        
        print("✅ All validations passed")
        
        # Get user ID from session - prefer UID, fallback to email
        user_id = session.get('user_uid', session['user_email'])
        print(f"🆔 Using user ID: {user_id}")
        
        # For now, let's just simulate saving the goal without Firestore
        # to isolate the authentication issue
        goal_data = {
            'title': data.get('title', '').strip(),
            'description': data.get('description', '').strip() or data.get('type'),
            'targetValue': int(data.get('targetValue')) if data.get('targetValue') else 0,
            'currentValue': int(data.get('currentValue', 0)),
            'targetDate': data.get('targetDate'),
            'type': data.get('type'),
            'userID': user_id,
            'status': 'In Progress'
        }
        
        print(f"📋 Goal data prepared: {goal_data}")
        
        # Parse the target date for Firestore
        target_date_str = data.get('targetDate')
        target_date = datetime.strptime(target_date_str, '%Y-%m-%d')
        current_time = datetime.now()
        
        # Create goal data structure matching your Firebase schema
        firestore_data = {
            'title': goal_data['title'],
            'description': goal_data['description'],
            'targetValue': goal_data['targetValue'],
            'currentValue': goal_data['currentValue'],
            'createdAt': current_time,
            'startDate': current_time,
            'endDate': target_date,
            'status': 'In Progress',
            'habitID': '',
            'userID': user_id
        }
        
        print(f"� Attempting to save to Firestore...")
        
        # Try REST API first (more reliable)
        goal_id = firestore_rest_api_create('goals', firestore_data)
        
        if goal_id:
            print(f"✅ Successfully saved via REST API with ID: {goal_id}")
        else:
            print("⚠️  REST API failed, falling back to Admin SDK...")
            
            # Fallback to Admin SDK if REST API fails
            if db:
                try:
                    result_container = {'success': False, 'doc_id': None, 'error': None}
                    
                    def firestore_operation():
                        try:
                            print("� SDK Thread: Starting Firestore write...")
                            doc_ref = db.collection('goals').document()
                            doc_ref.set(firestore_data)
                            result_container['success'] = True
                            result_container['doc_id'] = doc_ref.id
                            print(f"✅ SDK Thread: Write completed! ID: {doc_ref.id}")
                        except Exception as e:
                            result_container['error'] = str(e)
                            print(f"💥 SDK Thread: Write failed: {e}")
                    
                    print("🚀 Starting SDK thread with 5-second timeout...")
                    thread = threading.Thread(target=firestore_operation)
                    thread.daemon = True
                    thread.start()
                    thread.join(timeout=5.0)
                    
                    if thread.is_alive():
                        print("⏰ SDK operation timed out!")
                        raise Exception("Firestore SDK timeout")
                    elif result_container['success']:
                        goal_id = result_container['doc_id']
                        print(f"✅ Successfully saved via SDK with ID: {goal_id}")
                    elif result_container['error']:
                        raise Exception(result_container['error'])
                        
                except Exception as sdk_error:
                    print(f"💥 SDK error: {sdk_error}")
                    return jsonify({
                        'success': False,
                        'message': 'Failed to save goal to database',
                        'error': 'Both REST API and Admin SDK failed'
                    }), 500
        
        if not goal_id:
            return jsonify({
                'success': False,
                'message': 'Failed to save goal to database',
                'error': 'All save methods failed'
            }), 500
        
        print(f"🎉 Returning success response with goal ID: {goal_id}")
        return jsonify({
            'success': True,
            'message': 'Goal created successfully! 🎯',
            'goalId': goal_id
        }), 200
        
    except Exception as e:
        print(f"💥 CRITICAL ERROR in create_goal: {e}")
        import traceback
        print(f"📚 Full traceback: {traceback.format_exc()}")
        return jsonify({'error': f'Failed to create goal: {str(e)}'}), 500

@app.route('/get-goals', methods=['GET'])
def get_goals():
    """Get user goals from Firestore"""
    print(f"📊 GET-GOALS ENDPOINT CALLED")
    print(f"📍 Client IP: {request.remote_addr}")
    print(f"🔐 Session data: {dict(session)}")
    
    if 'user_email' not in session:
        print("❌ Not authenticated - no user_email in session")
        return jsonify({'error': 'Authentication required'}), 401
    
    print(f"✅ User authenticated: {session.get('user_email')}")
    
    try:
        user_id = session.get('user_uid', session['user_email'])
        print(f"🆔 Fetching goals for user: {user_id}")
        
        # Query goals for the current user
        goals_ref = db.collection('goals')
        query = goals_ref.where('userID', '==', user_id)
        docs = query.stream()
        
        goals = []
        for doc in docs:
            goal_data = doc.to_dict()
            goal_data['id'] = doc.id
            
            # Convert Firestore timestamps to readable format
            if 'createdAt' in goal_data and goal_data['createdAt']:
                goal_data['createdAt'] = goal_data['createdAt'].isoformat()
            if 'startDate' in goal_data and goal_data['startDate']:
                goal_data['startDate'] = goal_data['startDate'].isoformat()
            if 'endDate' in goal_data and goal_data['endDate']:
                goal_data['endDate'] = goal_data['endDate'].isoformat()
                
            goals.append(goal_data)
        
        print(f"✅ Successfully fetched {len(goals)} goals from Firestore")
        return jsonify({
            'success': True,
            'goals': goals
        }), 200
        
    except Exception as e:
        print(f"💥 Error fetching goals from Firestore: {e}")
        import traceback
        print(f"📚 Traceback: {traceback.format_exc()}")
        return jsonify({
            'success': False,
            'error': 'Failed to fetch goals from database'
        }), 500

@app.route('/debug-session')
def debug_session():
    """Debug session information"""
    return jsonify({
        'session_data': dict(session),
        'user_email': session.get('user_email'),
        'user_uid': session.get('user_uid'),
        'authenticated': 'user_email' in session
    })

@app.route('/test-goal', methods=['POST'])
def test_goal():
    """Test goal creation with minimal validation"""
    if not db:
        return jsonify({'error': 'Database unavailable'}), 500
    
    try:
        # Create a simple test goal
        test_data = {
            'title': 'Test Goal',
            'description': 'Test Description',
            'targetValue': 10,
            'currentValue': 0,
            'createdAt': datetime.now(),
            'startDate': datetime.now(),
            'endDate': datetime.now(),
            'status': 'In Progress',
            'habitID': '',
            'userID': 'test_user'
        }
        
        doc_ref = db.collection('goals').document()
        doc_ref.set(test_data)
        
        return jsonify({
            'success': True,
            'message': 'Test goal created!',
            'goalId': doc_ref.id
        }), 200
        
    except Exception as e:
        import traceback
        return jsonify({
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500

@app.route('/update-goal/<goal_id>', methods=['PUT'])
def update_goal(goal_id):
    """Update an existing goal"""
    print(f"📝 UPDATE-GOAL called for ID: {goal_id}")
    
    if 'user_email' not in session:
        return jsonify({'error': 'Authentication required'}), 401
    
    try:
        data = request.get_json()
        user_id = session.get('user_uid', session['user_email'])
        print(f"👤 User: {user_id}, Update data: {data}")
        
        # Read project_id from credentials
        with open('firebase-credentials.json', 'r') as f:
            creds = json.load(f)
            project_id = creds['project_id']
        
        # Build the Firestore REST API URL
        base_url = f"https://firestore.googleapis.com/v1/projects/{project_id}/databases/(default)/documents/goals/{goal_id}"
        
        # First, try to get the document to verify it exists and belongs to user
        print(f"🔍 Fetching goal from Firestore...")
        try:
            get_response = requests.get(base_url, timeout=5)
            print(f"📡 GET Response status: {get_response.status_code}")
            
            if get_response.status_code == 404:
                print("❌ Goal not found")
                return jsonify({'error': 'Goal not found'}), 404
            
            if get_response.status_code == 200:
                existing_doc = get_response.json()
                existing_fields = existing_doc.get('fields', {})
                
                # Verify ownership
                existing_user_id = existing_fields.get('userID', {}).get('stringValue', '')
                print(f"🔐 Verifying ownership: {existing_user_id} vs {user_id}")
                
                if existing_user_id != user_id:
                    return jsonify({'error': 'Unauthorized access to goal'}), 403
                
                # Prepare update - merge with existing fields
                update_fields = {**existing_fields}
                
                # Update currentValue if provided
                if 'currentValue' in data:
                    update_fields['currentValue'] = {'integerValue': str(data['currentValue'])}
                
                # Update status if provided
                if 'status' in data:
                    update_fields['status'] = {'stringValue': data['status']}
                
                # Update timestamp
                update_fields['updatedAt'] = {'timestampValue': datetime.now().isoformat() + 'Z'}
                
                # Optional fields
                if 'title' in data:
                    update_fields['title'] = {'stringValue': data['title']}
                if 'description' in data:
                    update_fields['description'] = {'stringValue': data['description']}
                if 'targetValue' in data:
                    update_fields['targetValue'] = {'integerValue': str(data['targetValue'])}
                if 'endDate' in data:
                    update_fields['endDate'] = {'timestampValue': datetime.strptime(data['endDate'], '%Y-%m-%d').isoformat() + 'Z'}
                
                # Update via REST API using PATCH
                update_payload = {'fields': update_fields}
                print(f"📤 Updating goal...")
                
                update_response = requests.patch(base_url, json=update_payload, timeout=5)
                print(f"📡 UPDATE Response status: {update_response.status_code}")
                
                if update_response.status_code in [200, 201]:
                    print(f"✅ Goal updated successfully")
                    return jsonify({
                        'success': True,
                        'message': 'Goal updated successfully!'
                    }), 200
                else:
                    print(f"❌ Update failed: {update_response.text}")
                    return jsonify({'error': 'Failed to update goal'}), 500
            
            else:
                # If we can't get the document, try fallback using Admin SDK
                print("⚠️ REST API failed, trying Admin SDK...")
                if db:
                    doc_ref = db.collection('goals').document(goal_id)
                    doc = doc_ref.get()
                    
                    if not doc.exists:
                        return jsonify({'error': 'Goal not found'}), 404
                    
                    goal_data = doc.to_dict()
                    if goal_data.get('userID') != user_id:
                        return jsonify({'error': 'Unauthorized access to goal'}), 403
                    
                    # Update using SDK
                    update_data = {}
                    if 'currentValue' in data:
                        update_data['currentValue'] = data['currentValue']
                    if 'status' in data:
                        update_data['status'] = data['status']
                    update_data['updatedAt'] = datetime.now()
                    
                    doc_ref.update(update_data)
                    
                    print("✅ Goal updated via Admin SDK")
                    return jsonify({
                        'success': True,
                        'message': 'Goal updated successfully!'
                    }), 200
                else:
                    return jsonify({'error': 'Database connection unavailable'}), 500
                
        except requests.exceptions.Timeout:
            print("⏰ Request timed out")
            return jsonify({'error': 'Request timed out'}), 500
        except requests.exceptions.RequestException as e:
            print(f"💥 Request exception: {e}")
            return jsonify({'error': f'Network error: {str(e)}'}), 500
        
    except Exception as e:
        print(f"💥 Error updating goal: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Failed to update goal: {str(e)}'}), 500

@app.route('/delete-goal/<goal_id>', methods=['DELETE'])
def delete_goal(goal_id):
    """Delete a goal"""
    print(f"🗑️ DELETE-GOAL called for ID: {goal_id}")
    
    if 'user_email' not in session:
        print("❌ Not authenticated")
        return jsonify({'error': 'Authentication required'}), 401
    
    try:
        user_id = session.get('user_uid', session['user_email'])
        print(f"👤 User: {user_id}")
        
        # Use Admin SDK for delete (more reliable than REST API DELETE)
        if db:
            print("🔍 Fetching goal from Firestore...")
            doc_ref = db.collection('goals').document(goal_id)
            
            # Use threading to prevent timeout
            result_container = {'success': False, 'error': None, 'exists': False, 'authorized': False}
            
            def delete_operation():
                try:
                    print("� Thread: Getting document...")
                    doc = doc_ref.get()
                    
                    if not doc.exists:
                        print("❌ Thread: Goal not found")
                        result_container['error'] = 'Goal not found'
                        return
                    
                    result_container['exists'] = True
                    goal_data = doc.to_dict()
                    goal_user_id = goal_data.get('userID', '')
                    
                    print(f"🔐 Thread: Verifying ownership: {goal_user_id} vs {user_id}")
                    
                    if goal_user_id != user_id:
                        print("❌ Thread: Unauthorized")
                        result_container['error'] = 'Unauthorized access to goal'
                        return
                    
                    result_container['authorized'] = True
                    
                    # Delete the document
                    print("🗑️ Thread: Deleting document...")
                    doc_ref.delete()
                    result_container['success'] = True
                    print("✅ Thread: Delete completed!")
                    
                except Exception as e:
                    result_container['error'] = str(e)
                    print(f"💥 Thread: Error: {e}")
            
            # Run in thread with timeout
            print("🚀 Starting delete thread with 5-second timeout...")
            thread = threading.Thread(target=delete_operation)
            thread.daemon = True
            thread.start()
            thread.join(timeout=5.0)
            
            if thread.is_alive():
                print("⏰ Delete operation timed out!")
                return jsonify({'error': 'Operation timed out'}), 500
            elif result_container['success']:
                print("✅ Goal deleted successfully")
                return jsonify({
                    'success': True,
                    'message': 'Goal deleted successfully!'
                }), 200
            elif not result_container['exists']:
                print("❌ Goal not found")
                return jsonify({'error': 'Goal not found'}), 404
            elif not result_container['authorized']:
                print("❌ Unauthorized")
                return jsonify({'error': 'Unauthorized access to goal'}), 403
            elif result_container['error']:
                print(f"❌ Error: {result_container['error']}")
                return jsonify({'error': result_container['error']}), 500
            else:
                print("❌ Unknown error")
                return jsonify({'error': 'Failed to delete goal'}), 500
        else:
            print("❌ Database not available")
            return jsonify({'error': 'Database connection unavailable'}), 500
        
    except Exception as e:
        print(f"💥 Error deleting goal: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Failed to delete goal: {str(e)}'}), 500

@app.route('/api/habits', methods=['GET', 'POST'])
def habits_api():
    """Habits API endpoint"""
    if 'user_email' not in session:
        return jsonify({'error': 'Authentication required'}), 401
    
    user_id = session.get('user_uid', session['user_email'])
    
    if request.method == 'GET':
        # Get user habits
        if db:
            try:
                habits_ref = db.collection('habits')
                query = habits_ref.where('userID', '==', user_id)
                docs = query.stream()
                
                habits = []
                for doc in docs:
                    habit_data = doc.to_dict()
                    habit_data['id'] = doc.id
                    habits.append(habit_data)
                
                return jsonify({'success': True, 'habits': habits}), 200
            except Exception as e:
                return jsonify({'error': str(e)}), 500
        else:
            return jsonify({'success': True, 'habits': []}), 200
    
    elif request.method == 'POST':
        # Create new habit
        if not db:
            return jsonify({'error': 'Database connection unavailable'}), 500
        
        try:
            data = request.get_json()
            habit_data = {
                'name': data.get('name'),
                'description': data.get('description', ''),
                'category': data.get('category', 'general'),
                'frequency': data.get('frequency', 'daily'),
                'userID': user_id,
                'createdAt': datetime.now(),
                'isActive': True
            }
            
            doc_ref = db.collection('habits').document()
            doc_ref.set(habit_data)
            
            return jsonify({
                'success': True,
                'message': 'Habit created successfully!',
                'habitId': doc_ref.id
            }), 200
            
        except Exception as e:
            return jsonify({'error': str(e)}), 500

@app.route('/api/habits/<habit_id>', methods=['DELETE'])
def delete_habit(habit_id):
    """Delete a habit"""
    print(f"🗑️ DELETE-HABIT called for ID: {habit_id}")
    
    if 'user_email' not in session:
        return jsonify({'error': 'Authentication required'}), 401
    
    if not db:
        return jsonify({'error': 'Database connection unavailable'}), 500
    
    try:
        user_id = session.get('user_uid', session['user_email'])
        
        # Get the habit to verify ownership
        habit_ref = db.collection('habits').document(habit_id)
        habit = habit_ref.get()
        
        if not habit.exists:
            return jsonify({'error': 'Habit not found'}), 404
        
        habit_data = habit.to_dict()
        
        # Verify the habit belongs to the user
        if habit_data.get('userID') != user_id:
            return jsonify({'error': 'Unauthorized to delete this habit'}), 403
        
        # Delete the habit
        habit_ref.delete()
        print(f"✅ Habit {habit_id} deleted successfully")
        
        return jsonify({
            'success': True,
            'message': 'Habit deleted successfully'
        }), 200
        
    except Exception as e:
        print(f"💥 Error deleting habit: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Failed to delete habit: {str(e)}'}), 500

@app.route('/test-connection')
def test_connection():
    """Simple endpoint to test server connectivity"""
    print("🔗 Test connection endpoint called")
    return jsonify({
        'status': 'Server is responding',
        'timestamp': datetime.now().isoformat(),
        'session_active': 'user_email' in session
    }), 200

@app.route('/test-firestore-simple')
def test_firestore_simple():
    """Simple Firestore test without threading"""
    print("🔥 Simple Firestore test...")
    
    if not db:
        return jsonify({'error': 'Firestore not initialized'}), 500
    
    try:
        print("📝 Attempting to write to Firestore...")
        test_doc = db.collection('test').document('connection_test')
        test_doc.set({
            'timestamp': datetime.now(),
            'test': 'Simple write test'
        })
        print("✅ Write successful!")
        
        print("📖 Attempting to read from Firestore...")
        doc = test_doc.get()
        print(f"✅ Read successful! Data: {doc.to_dict()}")
        
        return jsonify({
            'success': True,
            'message': 'Firestore connection working!',
            'data': doc.to_dict()
        }), 200
        
    except Exception as e:
        print(f"💥 Firestore error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'error': str(e),
            'type': type(e).__name__
        }), 500

@app.route('/test-firestore')
def test_firestore():
    """Test Firestore connection and rules"""
    print("🔥 Testing Firestore connection...")
    
    if not db:
        return jsonify({
            'error': 'Firestore client not initialized'
        }), 500
    
    try:
        # Test simple write operation
        test_data = {
            'test': True,
            'timestamp': datetime.now(),
            'message': 'Firestore connection test'
        }
        
        print(f"📤 Testing Firestore write: {test_data}")
        
        # Use the same timeout mechanism as goal creation
        result_container = {'success': False, 'doc_id': None, 'error': None}
        
        def firestore_test():
            try:
                doc_ref = db.collection('test').document()
                doc_ref.set(test_data)
                result_container['success'] = True
                result_container['doc_id'] = doc_ref.id
                print(f"✅ Test write successful: {doc_ref.id}")
            except Exception as e:
                result_container['error'] = str(e)
                print(f"💥 Test write failed: {e}")
        
        thread = threading.Thread(target=firestore_test)
        thread.daemon = True
        thread.start()
        thread.join(timeout=5.0)
        
        if thread.is_alive():
            return jsonify({
                'error': 'Firestore operation timed out',
                'details': 'Connection is hanging - check Firebase credentials'
            }), 500
        elif result_container['success']:
            return jsonify({
                'success': True,
                'message': 'Firestore connection working!',
                'test_doc_id': result_container['doc_id']
            }), 200
        else:
            return jsonify({
                'error': 'Firestore write failed',
                'details': result_container['error']
            }), 500
            
    except Exception as e:
        print(f"💥 Firestore test error: {e}")
        return jsonify({
            'error': str(e)
        }), 500

@app.route('/firebase-debug')
def firebase_debug():
    """Firebase debugging page"""
    return render_template('firebase_debug.html')

if __name__ == '__main__':
    app.run(debug=True, host='127.0.0.1', port=5000)