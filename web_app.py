# web_app.py
import os, json, uuid, threading, requests, firebase_admin
from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from werkzeug.utils import secure_filename

# ---------------- Flask ---------------- #
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'your-secret-key-change-this-in-production')

app.config.update(
    SESSION_COOKIE_NAME='habit_session',
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
    SESSION_COOKIE_SECURE=False  # set True if you serve over HTTPS
)

# ---------------- Firebase Admin ---------------- #
from firebase_admin import auth, credentials, firestore, storage

try:
    try:
        firebase_admin.get_app()
        print("Firebase Admin SDK already initialized")
    except ValueError:
        cred = credentials.Certificate('firebase-credentials.json')  # keep this file in project root
        firebase_admin.initialize_app(cred, {
            "storageBucket": "kappa-36c9a.appspot.com"
        })
        print("Firebase Admin SDK initialized successfully")
except Exception as e:
    print(f"Firebase Admin SDK initialization failed: {e}")

try:
    db = firestore.client()
    print("Firestore client initialized successfully")
except Exception as e:
    print(f"Firestore initialization failed: {e}")
    db = None

# ---------------- Helpers ---------------- #
def require_auth():
    """
    If the user is not logged in, redirect to /login.
    If logged in, ensure we have a UID in session and return (email, uid).
    """
    if 'user_email' not in session:
        flash('Please log in to access this page', 'error')
        return redirect(url_for('login'))
    uid = session.get('user_uid') or ('temp_uid_' + session['user_email'].replace('@','_').replace('.','_'))
    session['user_uid'] = uid
    return session['user_email'], uid

def firestore_rest_create(collection, data):
    """
    Lightweight fallback to create a Firestore doc via REST if the Admin SDK path fails.
    Returns the created doc id or None.
    """
    try:
        with open('firebase-credentials.json', 'r') as f:
            project_id = json.load(f)['project_id']
        doc_id = str(uuid.uuid4())
        url = f"https://firestore.googleapis.com/v1/projects/{project_id}/databases/(default)/documents/{collection}/{doc_id}"

        def fval(v):
            if isinstance(v, bool):      return {'booleanValue': v}
            if isinstance(v, int):       return {'integerValue': str(v)}
            if isinstance(v, float):     return {'doubleValue': v}
            if isinstance(v, datetime):  return {'timestampValue': v.isoformat()+'Z'}
            return {'stringValue': str(v)}

        payload = {'fields': {k: fval(v) for k, v in data.items()}}
        r = requests.post(url, json=payload, timeout=5)
        if r.status_code in (200, 201):
            return doc_id
        print("[REST create] error:", r.status_code, r.text)
        return None
    except Exception as e:
        print("[REST create] exception:", e)
        return None
from datetime import datetime  # you already have this, it's fine if it repeats

def _ts_to_iso(v):
    """Safely convert Firestore Timestamp/datetime to ISO string for templates."""
    try:
        if hasattr(v, "isoformat"):
            return v.isoformat()
        if hasattr(v, "to_datetime"):
            return v.to_datetime().isoformat()
    except Exception:
        pass
    return str(v) if v is not None else None

# ---------------- Auth pages ---------------- #
@app.route('/login')
def login():  # the frontend (Firebase Web) handles sign-in; we only render the page
    return render_template('login.html')

@app.route('/signup')
def signup():  # optional
    return render_template('signup.html')

@app.route('/verify-token', methods=['POST'])
def verify_token():
    """
    Called from frontend with Firebase ID token.
    On success: store user_email and user_uid in session.
    Also auto-create Firestore profile if it doesn't exist.
    """
    print("🔐 /verify-token called")
    try:
        data = request.get_json(silent=True) or {}
        id_token = data.get('idToken')
        explicit_display_name = data.get('displayName')  # Get display name from request
        if not id_token:
            return jsonify({'error': 'No ID token provided'}), 400

        # Verify token with clock skew tolerance (10 seconds)
        # This helps with minor clock synchronization issues
        decoded = auth.verify_id_token(id_token, clock_skew_seconds=10)
        user_email = decoded['email']
        user_uid = decoded['uid']
        
        # Store in session
        session['user_email'] = user_email
        session['user_uid'] = user_uid
        print(f"✅ Token verified for {user_email} ({user_uid})")
        
        # Create/Update Firestore user document if it doesn't exist
        try:
            user_ref = db.collection('users').document(user_uid)
            user_doc = user_ref.get()
            
            if not user_doc.exists:
                print(f"📝 Creating new user document for {user_email}")
                from datetime import datetime
                
                # Try to get display name from multiple sources
                display_name = None
                
                # First try: from the explicit request data (most reliable)
                if explicit_display_name and explicit_display_name.strip():
                    display_name = explicit_display_name.strip()
                    print(f"📛 Got display name from request: {display_name}")
                
                # Second try: from the token
                elif decoded.get('name'):
                    display_name = decoded.get('name')
                    print(f"📛 Got display name from token: {display_name}")
                
                # Third try: get from Firebase Auth user record
                elif not display_name:
                    try:
                        user_record = auth.get_user(user_uid)
                        if user_record.display_name:
                            display_name = user_record.display_name
                            print(f"📛 Got display name from Firebase Auth: {display_name}")
                    except Exception as e:
                        print(f"⚠️ Could not get user record: {e}")
                
                # Fallback: use email prefix
                if not display_name:
                    display_name = user_email.split('@')[0].title()
                    print(f"📛 Using email prefix as display name: {display_name}")
                
                user_data = {
                    'uid': user_uid,
                    'email': user_email,
                    'displayName': display_name,
                    'friends': [],
                    'friendRequests': {'incoming': [], 'outgoing': []},
                    'stats': {'currentStreak': 0, 'longestStreak': 0, 'totalHabitsCompleted': 0},
                    'createdAt': datetime.now(),
                    'lastLoginAt': datetime.now()
                }
                user_ref.set(user_data)
                print(f"✅ Created user document for {user_email} with display name: {display_name}")
            else:
                # Update last login time for existing users and check display name
                from datetime import datetime
                existing_data = user_doc.to_dict()
                updates = {'lastLoginAt': datetime.now()}
                
                # Check if we need to update display name
                current_display_name = existing_data.get('displayName', '')
                
                # If current display name looks like email-based, try to update it
                if (not current_display_name or 
                    current_display_name == user_email.split('@')[0].title() or
                    '@' in current_display_name):
                    
                    # Try to get better display name
                    better_display_name = None
                    
                    # First try: from explicit request
                    if explicit_display_name and explicit_display_name.strip():
                        better_display_name = explicit_display_name.strip()
                        print(f"📛 Updating display name from request: {better_display_name}")
                    
                    # Second try: from Firebase Auth user record
                    elif not better_display_name:
                        try:
                            user_record = auth.get_user(user_uid)
                            if user_record.display_name and user_record.display_name != current_display_name:
                                better_display_name = user_record.display_name
                                print(f"📛 Updating display name from Firebase Auth: {better_display_name}")
                        except Exception as e:
                            print(f"⚠️ Could not get user record for update: {e}")
                    
                    if better_display_name:
                        updates['displayName'] = better_display_name
                
                user_ref.update(updates)
                print(f"🔄 Updated user data for {user_email}")
                
        except Exception as firestore_error:
            print(f"⚠️ Could not create/update user document: {firestore_error}")
            # Don't fail the login if Firestore fails
        
        return jsonify({'success': True}), 200

    except Exception as e:
        print("💥 Token verification error:", e)
        return jsonify({'error': 'Invalid token'}), 401


@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out successfully', 'success')
    return redirect(url_for('login'))

# ---------------- Index / Dashboard shell ---------------- #
@app.route('/')
def index():
    return redirect(url_for('dashboard') if 'user_email' in session else url_for('login'))

@app.route('/dashboard', endpoint='dashboard')
def dashboard():
    auth_result = require_auth()
    if not isinstance(auth_result, tuple):
        return auth_result
    user_email, user_uid = auth_result
    return render_template('dashboard.html',
                           user_email=user_email,
                           user_uid=user_uid,
                           active_tab='home')

# ---------------- Top Nav Pages ---------------- #
@app.route('/create', endpoint='create_page')
def create_page():
    auth_result = require_auth()
    if not isinstance(auth_result, tuple):
        return auth_result
    user_email, user_uid = auth_result
    return render_template('create.html',
                           user_email=user_email,
                           user_uid=user_uid,
                           active_tab='create')

from datetime import date, timedelta

@app.route('/analytics', endpoint='analytics_page')
def analytics_page():
    auth_result = require_auth()
    if not isinstance(auth_result, tuple):
        return auth_result
    user_email, user_uid = auth_result
    today = date.today()
    today_str = today.strftime("%Y-%m-%d")
    last_30_days = []

    habits = []
    habit_stats = {}
    all_completed_dates = set()

    try:
        # FETCH HABITS
        habit_docs = db.collection("habits") \
                       .where("userID", "==", user_uid) \
                       .stream()

        for d in habit_docs:
            h = d.to_dict()
            h["id"] = d.id
            habits.append(h)

        # FETCH COMPLETIONS PER HABIT
        for h in habits:
            habit_id = h["id"]

            completion_docs = db.collection("habit_completions") \
                 .where("userID", "==", user_uid) \
                 .where("habitID", "==", habit_id) \
                 .stream()

            completed_dates = {doc.to_dict().get("date") for doc in completion_docs}

            # Add to combined calendar
            all_completed_dates.update(completed_dates)

            # Weekly + streak stats
            week_data, weekly_count, streak_current, streak_longest = compute_weekly_stats(completed_dates)

            # last 30 days for mini calendar (today)
            last30 = [(today - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(29, -1, -1)]

            habit_stats[habit_id] = {
                "completed_dates": list(completed_dates),
                "week_data": week_data,
                "weekly_count": weekly_count,
                "current": streak_current,
                "longest": streak_longest,
                "last30": last30,
            }

        # Build 30-day calendar for page
        last_30 = [(today - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(29, -1, -1)]
        last_30_days = [
            {"date": d, "done": d in all_completed_dates}
            for d in last_30
        ]

    except Exception as e:
        print("[Analytics Error]", e)
        # last_30_days 

    return render_template(
        "analytics.html",
        today=today_str,
        habits=habits,
        habit_stats=habit_stats,
        last_30_days=last_30_days,
        completed_global=list(all_completed_dates),
        active_tab="analytics",
    )


# ============================================================================
# FRIENDS FEATURE - PAGE ROUTE
# Renders the friends management page with authentication
# ============================================================================
@app.route('/friends', endpoint='friends_page')
def friends_page():
    """Render the friends page - main entry point for friends feature"""
    auth_result = require_auth()
    if not isinstance(auth_result, tuple):
        return auth_result
    user_email, user_uid = auth_result
    return render_template('friends.html',
                           user_email=user_email,
                           user_uid=user_uid,
                           active_tab='friends')

# -------------------------------------------------------
# Helper Functions
# -------------------------------------------------------

def calculate_max_habit_streak(user_uid):
    """Calculate the maximum current streak from all habits of a user"""
    try:
        print(f"🔥 Calculating max streak for user: {user_uid}")
        
        if not db:
            print("❌ Database not initialized")
            return 0
        
        # Get all habits for this user
        habits_docs = db.collection('habits').where('userID', '==', user_uid).stream()
        habits = []
        for doc in habits_docs:
            habit_data = doc.to_dict()
            if habit_data:  # Check if data exists
                habit_data['id'] = doc.id
                habits.append(habit_data)
        
        print(f"📊 Found {len(habits)} habits for user {user_uid}")
        
        if not habits:
            print(f"📭 No habits found for user {user_uid}")
            return 0
        
        max_streak = 0
        
        for habit in habits:
            try:
                # Get current streak directly from habit document
                current_streak = habit.get('currentStreak', 0)
                habit_name = habit.get('name', 'Unknown')
                print(f"🎯 Habit '{habit_name}': {current_streak} day streak")
                
                max_streak = max(max_streak, current_streak)
                
            except Exception as habit_error:
                print(f"⚠️ Error processing habit {habit.get('name', 'Unknown')}: {habit_error}")
                continue
        
        print(f"🏆 Max streak for user {user_uid}: {max_streak}")
        return max_streak
        
    except Exception as e:
        print(f"❌ Error calculating max streak for user {user_uid}: {e}")
        import traceback
        print(f"❌ Traceback: {traceback.format_exc()}")
        return 0

def calculate_current_streak(completed_dates):
    """Calculate current streak from a list of completion dates"""
    if not completed_dates:
        return 0
    
    from datetime import datetime, timedelta
    
    # Sort dates in descending order (most recent first)
    sorted_dates = sorted(set(completed_dates), reverse=True)
    
    today = datetime.now().date()
    current_streak = 0
    
    # Check if completed today or yesterday to start counting
    if sorted_dates[0] == today or sorted_dates[0] == (today - timedelta(days=1)):
        current_streak = 1
        last_date = sorted_dates[0]
        
        # Count consecutive days backwards
        for i in range(1, len(sorted_dates)):
            expected_date = last_date - timedelta(days=1)
            if sorted_dates[i] == expected_date:
                current_streak += 1
                last_date = sorted_dates[i]
            else:
                break
    
    return current_streak

# ============================================================================
# FRIENDS FEATURE - API ENDPOINTS
# Complete friends management system with streak tracking
# ============================================================================

@app.route('/api/friends', methods=['GET'])
def get_friends():
    """Get user's friends list with their stats"""
    print("📊 GET-FRIENDS ENDPOINT CALLED")
    print(f"📍 Session data: {dict(session)}")
    
    if 'user_uid' not in session:
        print("❌ Not authenticated - no user_uid in session")
        return jsonify({'error': 'Authentication required'}), 401
    
    try:
        user_uid = session['user_uid']
        print(f"✅ User authenticated: {user_uid}")
        
        # Get current user's data
        user_ref = db.collection('users').document(user_uid)
        user_doc = user_ref.get()
        
        if not user_doc.exists:
            print(f"❌ User document not found for uid: {user_uid}")
            return jsonify({'error': 'User not found'}), 404
        
        user_data = user_doc.to_dict()
        friends_list = user_data.get('friends', [])
        print(f"📋 Friends list: {friends_list}")
        
        # Get friend requests data ALWAYS (even if no friends)
        friend_requests = user_data.get('friendRequests', {})
        incoming_requests = friend_requests.get('incoming', [])
        outgoing_requests = friend_requests.get('outgoing', [])
        
        print(f"📥 Incoming requests: {incoming_requests}")
        print(f"📤 Outgoing requests: {outgoing_requests}")
        
        # Get friends data
        friends_data = []
        if friends_list:
            print(f"👥 Processing {len(friends_list)} friends")
        else:
            print("📭 No friends yet")
        
        # Get friends' data
        friends_data = []
        for friend_uid in friends_list:
            friend_ref = db.collection('users').document(friend_uid)
            friend_doc = friend_ref.get()
            
            if friend_doc.exists:
                friend_info = friend_doc.to_dict()
                
                # Calculate friend's maximum habit streak
                max_streak = calculate_max_habit_streak(friend_uid)
                
                friends_data.append({
                    'uid': friend_uid,
                    'email': friend_info.get('email'),
                    'displayName': friend_info.get('displayName'),
                    'maxStreak': max_streak,
                    'stats': friend_info.get('stats', {
                        'currentStreak': 0,
                        'longestStreak': 0,
                        'totalHabitsCompleted': 0
                    })
                })
        
        # Get incoming requests details from Firestore
        incoming_data = []
        for requester_uid in incoming_requests:
            try:
                # Get from Firestore users collection
                requester_doc = db.collection('users').document(requester_uid).get()
                if requester_doc.exists:
                    requester_data = requester_doc.to_dict()
                    requester_info = {
                        'uid': requester_uid,
                        'email': requester_data.get('email'),
                        'displayName': requester_data.get('displayName', 'User'),
                        'stats': requester_data.get('stats', {}),
                        'type': 'incoming'
                    }
                    incoming_data.append(requester_info)
                    print(f"📋 Added incoming request: {requester_info['displayName']}")
            except Exception as e:
                print(f"⚠️ Could not get requester data for {requester_uid}: {e}")
                continue

        # Get outgoing requests details from Firestore
        outgoing_data = []
        for target_uid in outgoing_requests:
            try:
                # Get from Firestore users collection
                target_doc = db.collection('users').document(target_uid).get()
                if target_doc.exists:
                    target_data = target_doc.to_dict()
                    target_info = {
                        'uid': target_uid,
                        'email': target_data.get('email'),
                        'displayName': target_data.get('displayName', 'User'),
                        'stats': target_data.get('stats', {}),
                        'type': 'outgoing'
                    }
                    outgoing_data.append(target_info)
                    print(f"📤 Added outgoing request: {target_info['displayName']}")
            except Exception as e:
                print(f"⚠️ Could not get target user data for {target_uid}: {e}")
                continue

        print(f"✅ Successfully fetched {len(friends_data)} friends, {len(incoming_data)} incoming requests, and {len(outgoing_data)} outgoing requests")
        return jsonify({
            'success': True, 
            'friends': friends_data,
            'incomingRequests': incoming_data,
            'outgoingRequests': outgoing_data,
            'outgoingRequestCount': len(outgoing_requests)
        })
        
    except Exception as e:
        print(f"💥 Error getting friends: {e}")
        import traceback
        print(f"💥 Full traceback: {traceback.format_exc()}")
        return jsonify({'error': 'Failed to load friends'}), 500

@app.route('/api/friends/search', methods=['POST'])
def search_friend():
    """Search for a user by email"""
    print(f"\n🔍 ===== SEARCH FRIEND REQUEST =====")
    
    # Check authentication
    if 'user_uid' not in session:
        print(f"❌ User not authenticated - no user_uid in session")
        return jsonify({'error': 'Authentication required'}), 401
    
    current_user_uid = session['user_uid']
    print(f"✅ Authenticated user: {current_user_uid}")
    
    # Get email from request
    data = request.get_json()
    print(f"📦 Request data: {data}")
    
    if not data or 'email' not in data:
        print(f"❌ No email provided in request")
        return jsonify({'error': 'Email is required'}), 400
    
    search_email = data['email'].strip().lower()
    print(f"📧 Searching for email: {search_email}")
    
    try:
        # Search Firestore users collection for user with this email
        print(f"🔍 Searching Firestore users collection for email: {search_email}")
        users_ref = db.collection('users')
        query = users_ref.where('email', '==', search_email).limit(1)
        results = query.get()
        
        print(f"📊 Query results count: {len(results)}")
        
        if not results:
            print(f"❌ No user found with email: {search_email}")
            return jsonify({'success': False, 'error': 'User not found'}), 404
        
        # Get the user document
        user_doc = results[0]
        user_data = user_doc.to_dict()
        user_uid = user_data.get('uid')
        user_email = user_data.get('email')
        user_display_name = user_data.get('displayName', 'User')
        user_stats = user_data.get('stats', {'currentStreak': 0, 'longestStreak': 0, 'totalHabitsCompleted': 0})
        
        print(f"✅ Found user: {user_uid}")
        print(f"📋 User data: displayName={user_display_name}, email={user_email}")
        
        # Check if searching for yourself
        if user_uid == current_user_uid:
            print(f"❌ User trying to add themselves")
            return jsonify({'success': False, 'error': 'You cannot add yourself as a friend'}), 400
        
        # Check if already friends
        current_user_doc = db.collection('users').document(current_user_uid).get()
        current_user_data = current_user_doc.to_dict()
        friends_list = current_user_data.get('friends', [])
        
        print(f"👥 Current user's friends: {friends_list}")
        
        if user_uid in friends_list:
            print(f"⚠️ Already friends with this user")
            return jsonify({'success': False, 'error': 'You are already friends with this user'}), 400
        
        # Return user data
        user_response = {
            'uid': user_uid,
            'email': user_email,
            'displayName': user_display_name,
            'stats': user_stats
        }
        
        print(f"✅ Returning user data: {user_response}")
        return jsonify({'success': True, 'user': user_response}), 200
        
    except Exception as e:
        print(f"💥 Error searching for user: {e}")
        import traceback
        print(f"💥 Full traceback: {traceback.format_exc()}")
        return jsonify({'success': False, 'error': 'An error occurred while searching'}), 500

@app.route('/api/friends/add', methods=['POST'])
def add_friend():
    """Add friend directly by UID"""
    print(f"\n➕ ===== ADD FRIEND REQUEST =====")
    
    # Check authentication
    if 'user_uid' not in session:
        print(f"❌ User not authenticated")
        return jsonify({'error': 'Authentication required'}), 401
    
    current_user_uid = session['user_uid']
    print(f"✅ Authenticated user: {current_user_uid}")
    
    try:
        data = request.get_json()
        print(f"📦 Request data: {data}")
        
        friend_uid = data.get('friendUid')
        
        if not friend_uid:
            print(f"❌ No friendUid provided")
            return jsonify({'error': 'Friend UID is required'}), 400
        
        print(f"👤 Friend UID to add: {friend_uid}")
        
        # Cannot add yourself
        if friend_uid == current_user_uid:
            print(f"❌ User trying to add themselves")
            return jsonify({'error': 'Cannot add yourself as a friend'}), 400
        
        # Verify friend exists in Firestore
        print(f"🔍 Verifying friend exists in Firestore: {friend_uid}")
        friend_ref = db.collection('users').document(friend_uid)
        friend_doc = friend_ref.get()
        
        if not friend_doc.exists:
            print(f"❌ Friend user not found in Firestore")
            return jsonify({'error': 'Friend user not found'}), 404
        
        friend_data = friend_doc.to_dict()
        print(f"✅ Friend found: {friend_data.get('email')}")
        
        # Get current user's Firestore document
        print(f"🔍 Getting current user Firestore data: {current_user_uid}")
        user_ref = db.collection('users').document(current_user_uid)
        user_doc = user_ref.get()
        
        if not user_doc.exists:
            print(f"❌ Current user document not found")
            return jsonify({'error': 'User document not found. Please log out and log back in.'}), 404
            
        user_data = user_doc.to_dict()
        print(f"✅ Current user data ready")
        
        # Check if already friends
        current_friends = user_data.get('friends', [])
        print(f"👥 Current friends list: {current_friends}")
        
        if friend_uid in current_friends:
            print(f"⚠️ Already friends")
            return jsonify({'error': 'Already friends with this user'}), 400
        
        print(f"✅ Friend data ready: {friend_data.get('displayName')}")
        
        # Check if request already sent
        current_outgoing = user_data.get('friendRequests', {}).get('outgoing', [])
        friend_incoming = friend_data.get('friendRequests', {}).get('incoming', [])
        
        if friend_uid in current_outgoing:
            print(f"⚠️ Friend request already sent")
            return jsonify({'error': 'Friend request already sent'}), 400
        
        # Send friend request
        print(f"📤 Sending friend request from {current_user_uid} to {friend_uid}")
        
        # Add to current user's outgoing requests
        user_ref.update({
            'friendRequests.outgoing': firestore.ArrayUnion([friend_uid])
        })
        print(f"✅ Added to outgoing requests")
        
        # Add to friend's incoming requests
        friend_ref.update({
            'friendRequests.incoming': firestore.ArrayUnion([current_user_uid])
        })
        print(f"✅ Added to incoming requests")
        
        response_message = f'Friend request sent to {friend_data.get("displayName", friend_data.get("email"))}!'
        print(f"🎉 Success: {response_message}")
        
        return jsonify({
            'success': True,
            'message': response_message
        })
    
    except Exception as e:
        print(f"Error adding friend: {e}")
        return jsonify({'error': 'Failed to add friend'}), 500

@app.route('/api/friends/accept', methods=['POST'])
def accept_friend_request():
    """Accept a friend request"""
    print(f"\n✅ ===== ACCEPT FRIEND REQUEST =====")
    
    if 'user_uid' not in session:
        return jsonify({'error': 'Authentication required'}), 401
    
    current_user_uid = session['user_uid']
    
    try:
        data = request.get_json()
        requester_uid = data.get('requesterUid')
        
        if not requester_uid:
            return jsonify({'error': 'Requester UID is required'}), 400
        
        print(f"👥 Accepting friend request from {requester_uid} to {current_user_uid}")
        
        # Update both users
        user_ref = db.collection('users').document(current_user_uid)
        requester_ref = db.collection('users').document(requester_uid)
        
        # Remove from incoming/outgoing requests and add to friends
        user_ref.update({
            'friendRequests.incoming': firestore.ArrayRemove([requester_uid]),
            'friends': firestore.ArrayUnion([requester_uid])
        })
        
        requester_ref.update({
            'friendRequests.outgoing': firestore.ArrayRemove([current_user_uid]),
            'friends': firestore.ArrayUnion([current_user_uid])
        })
        
        print(f"🎉 Friend request accepted!")
        return jsonify({'success': True, 'message': 'Friend request accepted!'})
        
    except Exception as e:
        print(f"Error accepting friend request: {e}")
        return jsonify({'error': 'Failed to accept friend request'}), 500

@app.route('/api/friends/decline', methods=['POST'])
def decline_friend_request():
    """Decline a friend request"""
    print(f"\n❌ ===== DECLINE FRIEND REQUEST =====")
    
    if 'user_uid' not in session:
        return jsonify({'error': 'Authentication required'}), 401
    
    current_user_uid = session['user_uid']
    
    try:
        data = request.get_json()
        requester_uid = data.get('requesterUid')
        
        if not requester_uid:
            return jsonify({'error': 'Requester UID is required'}), 400
        
        print(f"👎 Declining friend request from {requester_uid}")
        
        # Remove from incoming/outgoing requests
        user_ref = db.collection('users').document(current_user_uid)
        requester_ref = db.collection('users').document(requester_uid)
        
        user_ref.update({
            'friendRequests.incoming': firestore.ArrayRemove([requester_uid])
        })
        
        requester_ref.update({
            'friendRequests.outgoing': firestore.ArrayRemove([current_user_uid])
        })
        
        print(f"✅ Friend request declined")
        return jsonify({'success': True, 'message': 'Friend request declined'})
        
    except Exception as e:
        print(f"Error declining friend request: {e}")
        return jsonify({'error': 'Failed to decline friend request'}), 500

@app.route('/api/friends/cancel', methods=['POST'])
def cancel_friend_request():
    """Cancel an outgoing friend request"""
    print(f"\n🚫 ===== CANCEL FRIEND REQUEST =====")
    
    if 'user_uid' not in session:
        return jsonify({'error': 'Authentication required'}), 401
    
    current_user_uid = session['user_uid']
    
    try:
        data = request.get_json()
        target_uid = data.get('targetUid')
        
        if not target_uid:
            return jsonify({'error': 'Target UID is required'}), 400
        
        print(f"🚫 Canceling friend request to {target_uid}")
        
        # Remove from outgoing/incoming requests
        user_ref = db.collection('users').document(current_user_uid)
        target_ref = db.collection('users').document(target_uid)
        
        user_ref.update({
            'friendRequests.outgoing': firestore.ArrayRemove([target_uid])
        })
        
        target_ref.update({
            'friendRequests.incoming': firestore.ArrayRemove([current_user_uid])
        })
        
        print(f"✅ Friend request canceled")
        return jsonify({'success': True, 'message': 'Friend request canceled'})
        
    except Exception as e:
        print(f"Error canceling friend request: {e}")
        return jsonify({'error': 'Failed to cancel friend request'}), 500

@app.route('/api/friends/<friend_uid>', methods=['DELETE'])
def remove_friend(friend_uid):
    """Remove a friend"""
    if 'user_uid' not in session:
        return jsonify({'error': 'Authentication required'}), 401
    
    try:
        user_uid = session['user_uid']
        
        # Remove from current user's friends list
        user_ref = db.collection('users').document(user_uid)
        user_ref.update({
            'friends': firestore.ArrayRemove([friend_uid])
        })
        
        # Remove current user from friend's friends list
        friend_ref = db.collection('users').document(friend_uid)
        friend_ref.update({
            'friends': firestore.ArrayRemove([user_uid])
        })
        
        return jsonify({
            'success': True,
            'message': 'Friend removed successfully'
        })
    
    except Exception as e:
        print(f"Error removing friend: {e}")
        return jsonify({'error': 'Failed to remove friend'}), 500

# -------------------------------------------------------

@app.route('/explore', endpoint='explore_page')
def explore_page():
    auth_result = require_auth()
    if not isinstance(auth_result, tuple):
        return auth_result
    user_email, user_uid = auth_result
    return render_template('explore.html',
                           user_email=user_email,
                           user_uid=user_uid,
                           active_tab='explore')

@app.route('/meals', endpoint='meals_page')
def meals_page():
    auth_result = require_auth()
    if not isinstance(auth_result, tuple):
        return auth_result
    user_email, user_uid = auth_result
    
    # Check if user has an active meal plan
    user_meal_plan = None
    if db:
        try:
            # Get user's current meal plan enrollment
            user_doc = db.collection('users').document(user_uid).get()
            if user_doc.exists:
                user_data = user_doc.to_dict()
                user_meal_plan = user_data.get('currentMealPlan')
        except Exception as e:
            print(f"Error fetching meal plan: {e}")
    
    return render_template('meals.html',
                         user_email=user_email,
                         user_uid=user_uid,
                         active_tab='meals',
                         has_meal_plan=user_meal_plan is not None,
                         current_plan=user_meal_plan)

# ---------------- Meal Plan API Endpoints ---------------- #

# Predefined meal plans with all 5 diet types
MEAL_PLANS = {
    "vegan": {
        "name": "Vegan Meal Plan",
        "description": "Plant-based meals without any animal products",
        "meals": {
            "monday": {
                "breakfast": "Chia pudding with almond milk and berries",
                "lunch": "Quinoa & chickpea salad",
                "dinner": "Tofu stir-fry with mixed vegetables"
            },
            "tuesday": {
                "breakfast": "Avocado toast with hummus",
                "lunch": "Lentil soup with whole-grain bread",
                "dinner": "Veggie tacos with black beans"
            },
            "wednesday": {
                "breakfast": "Smoothie bowl (banana, peanut butter, oats)",
                "lunch": "Vegan Buddha bowl",
                "dinner": "Spaghetti with marinara & mushrooms"
            },
            "thursday": {
                "breakfast": "Overnight oats with fruit",
                "lunch": "Falafel wrap with tahini",
                "dinner": "Stuffed bell peppers"
            },
            "friday": {
                "breakfast": "Peanut butter toast & apple",
                "lunch": "Vegan fried rice",
                "dinner": "Coconut chickpea curry"
            },
            "saturday": {
                "breakfast": "Vegan pancakes & syrup",
                "lunch": "Pasta salad with veggies",
                "dinner": "Grilled veggie skewers & quinoa"
            },
            "sunday": {
                "breakfast": "Fruit salad & nuts",
                "lunch": "Tomato-basil soup & toast",
                "dinner": "Vegan burger & sweet potatoes"
            }
        }
    },
    "vegetarian": {
        "name": "Vegetarian Meal Plan",
        "description": "Balanced vegetarian diet with dairy and eggs",
        "meals": {
            "monday": {
                "breakfast": "Greek yogurt with fruit & honey",
                "lunch": "Paneer salad",
                "dinner": "Vegetable stir-fry with rice"
            },
            "tuesday": {
                "breakfast": "Oatmeal & banana",
                "lunch": "Cheese & avocado sandwich",
                "dinner": "Veggie lasagna"
            },
            "wednesday": {
                "breakfast": "Smoothie",
                "lunch": "Caprese salad",
                "dinner": "Mushroom risotto"
            },
            "thursday": {
                "breakfast": "Toast with jam",
                "lunch": "Chickpea wrap",
                "dinner": "Vegetable curry & naan"
            },
            "friday": {
                "breakfast": "Pancakes",
                "lunch": "Egg salad sandwich",
                "dinner": "Baked eggplant parmesan"
            },
            "saturday": {
                "breakfast": "Poha or upma",
                "lunch": "Vegetarian burrito",
                "dinner": "Zucchini noodles & pesto"
            },
            "sunday": {
                "breakfast": "Waffles",
                "lunch": "Tomato soup & grilled cheese",
                "dinner": "Vegetable paella"
            }
        }
    },
    "mediterranean": {
        "name": "Mediterranean Diet",
        "description": "Heart-healthy Mediterranean-style meals",
        "meals": {
            "monday": {
                "breakfast": "Greek yogurt & nuts",
                "lunch": "Grilled chicken salad",
                "dinner": "Salmon with roasted vegetables"
            },
            "tuesday": {
                "breakfast": "Whole-grain toast & olive oil",
                "lunch": "Tuna salad",
                "dinner": "Grilled shrimp & quinoa"
            },
            "wednesday": {
                "breakfast": "Fruit & cheese",
                "lunch": "Lentil soup",
                "dinner": "Chicken gyro with veggies"
            },
            "thursday": {
                "breakfast": "Avocado toast",
                "lunch": "Hummus & pita",
                "dinner": "Baked cod & greens"
            },
            "friday": {
                "breakfast": "Omelet with spinach",
                "lunch": "Greek salad",
                "dinner": "Whole-wheat pasta & tomatoes"
            },
            "saturday": {
                "breakfast": "Smoothie",
                "lunch": "Falafel bowl",
                "dinner": "Grilled fish"
            },
            "sunday": {
                "breakfast": "Yogurt & berries",
                "lunch": "Veggie mezze platter",
                "dinner": "Roasted chicken"
            }
        }
    },
    "keto": {
        "name": "Keto Diet",
        "description": "Low-carb, high-fat ketogenic meal plan",
        "meals": {
            "monday": {
                "breakfast": "Scrambled eggs & avocado",
                "lunch": "Chicken Caesar salad (no croutons)",
                "dinner": "Salmon & buttered broccoli"
            },
            "tuesday": {
                "breakfast": "Cheese omelet",
                "lunch": "Zucchini noodles & pesto",
                "dinner": "Steak & asparagus"
            },
            "wednesday": {
                "breakfast": "Bulletproof coffee & eggs",
                "lunch": "Tuna mayo salad",
                "dinner": "Chicken Alfredo (low-carb)"
            },
            "thursday": {
                "breakfast": "Egg muffins",
                "lunch": "Cobb salad",
                "dinner": "Pork chops & keto slaw"
            },
            "friday": {
                "breakfast": "Greek yogurt (low-carb)",
                "lunch": "Bunless burger",
                "dinner": "Shrimp & garlic butter"
            },
            "saturday": {
                "breakfast": "Keto pancakes",
                "lunch": "Chicken wings",
                "dinner": "Cauliflower pizza"
            },
            "sunday": {
                "breakfast": "Avocado eggs",
                "lunch": "Egg salad",
                "dinner": "Roasted duck"
            }
        }
    },
    "intermittent_fasting": {
        "name": "Intermittent Fasting (16:8)",
        "description": "16:8 fasting model - first meal at lunch",
        "meals": {
            "monday": {
                "breakfast": "",
                "lunch": "Chicken stir-fry",
                "dinner": "Salmon & quinoa"
            },
            "tuesday": {
                "breakfast": "",
                "lunch": "Rice bowl with tofu",
                "dinner": "Grilled chicken & veggies"
            },
            "wednesday": {
                "breakfast": "",
                "lunch": "Tuna sandwich",
                "dinner": "Beef stir-fry"
            },
            "thursday": {
                "breakfast": "",
                "lunch": "Chickpea wrap",
                "dinner": "Shrimp pasta"
            },
            "friday": {
                "breakfast": "",
                "lunch": "Burrito bowl",
                "dinner": "Fish tacos"
            },
            "saturday": {
                "breakfast": "",
                "lunch": "Veggie burger",
                "dinner": "Homemade pizza"
            },
            "sunday": {
                "breakfast": "",
                "lunch": "Soup & bread",
                "dinner": "Roast dinner"
            }
        }
    }
}

@app.route('/api/meal-plans', methods=['GET'])
def get_meal_plans():
    """Get all available meal plans"""
    if 'user_email' not in session:
        return jsonify({'error': 'Authentication required'}), 401
    
    plans = []
    for plan_type, plan_data in MEAL_PLANS.items():
        plans.append({
            'type': plan_type,
            'name': plan_data['name'],
            'description': plan_data['description']
        })
    
    return jsonify({'success': True, 'plans': plans}), 200

@app.route('/api/enroll-meal-plan', methods=['POST'])
def enroll_meal_plan():
    """Enroll user in a meal plan"""
    if 'user_email' not in session:
        return jsonify({'error': 'Authentication required'}), 401
    
    user_uid = session.get('user_uid')
    data = request.get_json()
    plan_type = data.get('planType')
    
    if not plan_type or plan_type not in MEAL_PLANS:
        return jsonify({'error': 'Invalid meal plan type'}), 400
    
    try:
        if not db:
            return jsonify({'error': 'Database unavailable'}), 500
        
        # Update user document with current meal plan
        db.collection('users').document(user_uid).update({
            'currentMealPlan': plan_type,
            'mealPlanStartDate': datetime.now(),
            'mealPlanStatus': 'active'
        })
        
        # Create or update meal plan document in meal_plans collection
        meal_plan_data = {
            'userID': user_uid,
            'planType': plan_type,
            'planName': MEAL_PLANS[plan_type]['name'],
            'weekStart': datetime.now(),
            'meals': MEAL_PLANS[plan_type]['meals'],
            'enrolledAt': datetime.now(),
            'status': 'active',
            'createdAt': datetime.now(),
            'updatedAt': datetime.now()
        }
        
        # Check if user already has a meal plan document
        existing_plans = db.collection('meal_plans')\
            .where('userID', '==', user_uid)\
            .where('status', '==', 'active')\
            .stream()
        
        # Cancel any existing active plans
        for plan in existing_plans:
            plan.reference.update({'status': 'cancelled', 'updatedAt': datetime.now()})
        
        # Create new meal plan
        db.collection('meal_plans').add(meal_plan_data)
        
        return jsonify({
            'success': True,
            'message': f'Enrolled in {MEAL_PLANS[plan_type]["name"]} successfully!'
        }), 200
        
    except Exception as e:
        print(f"Error enrolling in meal plan: {e}")
        return jsonify({'error': 'Failed to enroll in meal plan'}), 500

@app.route('/api/current-meal-plan', methods=['GET'])
def get_current_meal_plan():
    """Get user's current meal plan with meals"""
    if 'user_email' not in session:
        return jsonify({'error': 'Authentication required'}), 401
    
    user_uid = session.get('user_uid')
    
    try:
        if not db:
            return jsonify({'error': 'Database unavailable'}), 500
        
        # Get user's current meal plan
        user_doc = db.collection('users').document(user_uid).get()
        if not user_doc.exists:
            return jsonify({'success': True, 'hasPlan': False}), 200
        
        user_data = user_doc.to_dict()
        plan_type = user_data.get('currentMealPlan')
        
        if not plan_type:
            return jsonify({'success': True, 'hasPlan': False}), 200
        
        if plan_type not in MEAL_PLANS:
            return jsonify({'error': 'Invalid meal plan'}), 400
        
        plan_data = MEAL_PLANS[plan_type]
        
        return jsonify({
            'success': True,
            'hasPlan': True,
            'plan': {
                'type': plan_type,
                'name': plan_data['name'],
                'description': plan_data['description'],
                'meals': plan_data['meals'],
                'startDate': user_data.get('mealPlanStartDate'),
                'status': user_data.get('mealPlanStatus', 'active')
            }
        }), 200
        
    except Exception as e:
        print(f"Error fetching meal plan: {e}")
        return jsonify({'error': 'Failed to fetch meal plan'}), 500

@app.route('/api/cancel-meal-plan', methods=['POST'])
def cancel_meal_plan():
    """Cancel user's current meal plan"""
    if 'user_email' not in session:
        return jsonify({'error': 'Authentication required'}), 401
    
    user_uid = session.get('user_uid')
    
    try:
        if not db:
            return jsonify({'error': 'Database unavailable'}), 500
        
        # Update user document to remove meal plan
        db.collection('users').document(user_uid).update({
            'currentMealPlan': None,
            'mealPlanStatus': 'cancelled',
            'updatedAt': datetime.now()
        })
        
        # Update all active meal plans to cancelled in meal_plans collection
        meal_plans = db.collection('meal_plans')\
            .where('userID', '==', user_uid)\
            .where('status', '==', 'active')\
            .stream()
        
        for plan in meal_plans:
            plan.reference.update({'status': 'cancelled', 'updatedAt': datetime.now()})
        
        return jsonify({
            'success': True,
            'message': 'Meal plan cancelled successfully'
        }), 200
        
    except Exception as e:
        print(f"Error cancelling meal plan: {e}")
        return jsonify({'error': 'Failed to cancel meal plan'}), 500

@app.route('/api/delete-meal-day', methods=['POST'])
def delete_meal_day():
    """Delete a specific day from the meal plan"""
    if 'user_uid' not in session:
        return jsonify({'error': 'Authentication required'}), 401
    
    user_uid = session.get('user_uid')
    
    try:
        data = request.get_json()
        day = data.get('day')
        
        if not day:
            return jsonify({'error': 'Day is required'}), 400
        
        if not db:
            return jsonify({'error': 'Database unavailable'}), 500
        
        # Find the active meal plan
        meal_plans = db.collection('meal_plans')\
            .where('userID', '==', user_uid)\
            .where('status', '==', 'active')\
            .limit(1)\
            .stream()
        
        plan_doc = None
        for plan in meal_plans:
            plan_doc = plan
            break
        
        if not plan_doc:
            return jsonify({'error': 'No active meal plan found'}), 404
        
        # Delete the specific day's meals
        plan_doc.reference.update({
            f'meals.{day}': firestore.DELETE_FIELD,
            'updatedAt': datetime.now()
        })
        
        return jsonify({
            'success': True,
            'message': f'{day.capitalize()} meals deleted successfully'
        }), 200
        
    except Exception as e:
        print(f"Error deleting meal day: {e}")
        return jsonify({'error': 'Failed to delete meal day'}), 500

# ---------------- Profile ---------------- #
@app.route('/profile', endpoint='profile_page')
def profile_page():
    auth_result = require_auth()
    if not isinstance(auth_result, tuple):
        return auth_result
    user_email, user_uid = auth_result

    # ------------------ Default Profile Structure ------------------ #
    profile = {
        "email": user_email,
        "username": user_email.split("@")[0],
        "first_name": "",
        "last_name": "",
        "display_name": "",
        "avatar": f"https://api.dicebear.com/7.x/initials/svg?seed={user_email.split('@')[0]}"
    }

    # ------------------ Load from Firestore ------------------ #
    if db:
        try:
            doc = db.collection("profiles").document(user_email).get()
            if doc.exists:
                data = doc.to_dict() or {}

                profile.update({
                    "first_name": data.get("first_name", ""),
                    "last_name": data.get("last_name", ""),
                    "display_name": data.get("display_name", profile["username"]),
                    "avatar": data.get("avatar_url", profile["avatar"]),
                    "username": data.get("username", profile["username"])
                })
        except Exception as e:
            print("[profile_page] Firestore read error:", e)

    # ------------------ Stats (Habits + Journal) ------------------ #
    stats = {"active_habits": 0, "journal_entries": 0}
    try:
        if db:
            stats["active_habits"] = sum(
                1 for _ in db.collection('habits')
                             .where('userID', '==', user_uid)
                             .stream()
            )
            stats["journal_entries"] = sum(
                1 for _ in db.collection('journal_entries')
                             .where('userID', '==', user_uid)
                             .stream()
            )
    except Exception as e:
        print("[profile_page] stats error:", e)

    # ------------------ Recent Habits ------------------ #
    recent_habits = []
    try:
        if db:
            q = db.collection('habits').where('userID', '==', user_uid).limit(5)
            for d in q.stream():
                h = d.to_dict()
                recent_habits.append({
                    "name": h.get('name') or "Habit",
                    "frequency": h.get('frequency', '').title()
                })
    except Exception as e:
        print("[profile_page] recent habits error:", e)

    return render_template(
        'profile.html',
        profile=profile,
        stats=stats,
        recent_habits=recent_habits,
        active_tab='profile'
    )



@app.route('/edit-profile', methods=['GET', 'POST'], endpoint='edit_profile')
def edit_profile():
    auth_result = require_auth()
    if not isinstance(auth_result, tuple):
        return auth_result
    email, uid = auth_result

    profile_data = {
        "email": email,
        "username": email.split('@')[0],
        "first_name": "",
        "last_name": "",
        "display_name": "",
        "avatar_url": None
    }

    # Load current profile
    if db:
        try:
            doc = db.collection("profiles").document(email).get()
            if doc.exists:
                data = doc.to_dict() or {}
                profile_data.update(data)
        except Exception as e:
            print("[edit_profile GET] Firestore read error:", e)

    # Handle POST
    if request.method == 'POST':
        display = (request.form.get('display_name') or '').strip()
        username = (request.form.get('username') or '').strip()
        avatar_file = request.files.get('avatar')

        update_fields = {
            "display_name": display,
            "username": username,
            "updated_at": datetime.now()
        }

        # Avatar upload
        try:
            if avatar_file and avatar_file.filename:
                bucket = storage.bucket()
                key = f"users/avatars/{uid}/{secure_filename(f'{uid}_{int(datetime.now().timestamp())}.png')}"
                blob = bucket.blob(key)
                blob.upload_from_file(avatar_file, content_type=avatar_file.mimetype)
                blob.patch()

                avatar_url = blob.generate_signed_url(
                    version="v4",
                    expiration=timedelta(days=7),
                    method="GET"
                )

                update_fields["avatar_url"] = avatar_url
                update_fields["avatar_path"] = key
        except Exception as e:
            print("[edit_profile POST] Avatar upload error:", e)

        # Save
        try:
            db.collection("profiles").document(email).set(update_fields, merge=True)
            flash("Profile updated successfully!", "success")
        except Exception as e:
            print("[edit_profile POST] Firestore write error:", e)
            flash("Failed to update profile", "error")

        return redirect(url_for('profile_page'))

    return render_template(
        'edit_profile.html',
        profile=profile_data,
        user_email=email,
        user_uid=uid,
        active_tab='profile'
    )


# ---------------- Goals ---------------- #
@app.route('/get-goals')
def get_goals():
    if 'user_email' not in session:
        return jsonify({'error': 'Authentication required'}), 401
    try:
        user_id = session.get('user_uid', session['user_email'])
        goals = []
        if db:
            docs = db.collection('goals').where('userID', '==', user_id).stream()
            for d in docs:
                g = d.to_dict(); g['id'] = d.id
                for k in ('createdAt','startDate','endDate'):
                    if k in g and hasattr(g[k], 'isoformat'):
                        g[k] = g[k].isoformat()
                goals.append(g)
        return jsonify({'success': True, 'goals': goals}), 200
    except Exception as e:
        print("[get-goals] error:", e)
        return jsonify({'success': False, 'error': 'Failed to fetch goals'}), 500

@app.route('/create-goal', methods=['POST'])
def create_goal():
    if 'user_email' not in session:
        return jsonify({'error': 'Authentication required'}), 401
    try:
        data = request.get_json(silent=True) or {}
        title = (data.get('title') or '').strip()
        gtype = data.get('type')
        tdate = data.get('targetDate')

        if not title: return jsonify({'error': 'Goal title is required'}), 400
        if not gtype: return jsonify({'error': 'Goal type is required'}), 400
        if not tdate: return jsonify({'error': 'Target date is required'}), 400

        user_id = session.get('user_uid', session['user_email'])
        end_dt  = datetime.strptime(tdate, '%Y-%m-%d')
        now     = datetime.now()
        payload = {
            'title': title,
            'description': (data.get('description') or gtype),
            'targetValue': int(data.get('targetValue') or 0),
            'currentValue': int(data.get('currentValue') or 0),
            'createdAt': now, 'startDate': now, 'endDate': end_dt,
            'status': 'In Progress', 'habitID': '', 'userID': user_id
        }

        goal_id = firestore_rest_create('goals', payload)
        if not goal_id and db:
            doc_ref = db.collection('goals').document()
            doc_ref.set(payload)
            goal_id = doc_ref.id

        if not goal_id:
            return jsonify({'success': False, 'message': 'Failed to save goal'}), 500

        return jsonify({'success': True, 'message': 'Goal created successfully!', 'goalId': goal_id}), 200
    except Exception as e:
        print("[create-goal] error:", e)
        return jsonify({'error': 'Failed to create goal'}), 500



@app.route('/goal/<goal_id>/complete', methods=['POST'])
def complete_goal(goal_id):
    if 'user_email' not in session:
        return jsonify({'error': 'Authentication required'}), 401

    try:
        db.collection('goals').document(goal_id).update({
            'status': 'Completed',
            'updatedAt': datetime.now()
        })
        return jsonify({'success': True, 'message': 'Goal marked as complete!'}), 200

    except Exception as e:
        print("[complete-goal] error:", e)
        return jsonify({'error': 'Failed to complete goal'}), 500

@app.route('/update-goal/<goal_id>', methods=['PUT'])
def update_goal(goal_id):
    """Update goal progress or status"""
    if 'user_email' not in session:
        return jsonify({'error': 'Authentication required'}), 401

    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        update_data = {'updatedAt': datetime.now()}
        
        # Handle currentValue update
        if 'currentValue' in data:
            update_data['currentValue'] = data['currentValue']
        
        # Handle status update (for reopening goals)
        if 'status' in data:
            update_data['status'] = data['status']
        
        if len(update_data) == 1:  # Only updatedAt
            return jsonify({'error': 'No valid update fields provided'}), 400
        
        db.collection('goals').document(goal_id).update(update_data)
        return jsonify({'success': True}), 200

    except Exception as e:
        print("[update-goal] error:", e)
        return jsonify({'error': 'Failed to update goal'}), 500

@app.route('/delete-goal/<goal_id>', methods=['DELETE'])
def delete_goal(goal_id):
    """Delete a goal"""
    if 'user_email' not in session:
        return jsonify({'error': 'Authentication required'}), 401

    try:
        # Delete the goal document
        db.collection('goals').document(goal_id).delete()
        return jsonify({'success': True, 'message': 'Goal deleted successfully'}), 200

    except Exception as e:
        print("[delete-goal] error:", e)
        return jsonify({'error': 'Failed to delete goal'}), 500

# ---------------- Habits API ---------------- #
@app.route('/api/habits', methods=['GET', 'POST'])
def habits_api():
    # Must be logged in
    if 'user_email' not in session:
        return jsonify({'error': 'Authentication required'}), 401

    user_id = session.get('user_uid', session['user_email'])
    user_email = session.get('user_email')

    # ---------- GET: fetch habits for dashboard ---------- #
    if request.method == 'GET':
        print(f"[habits_api GET] user_id={user_id}, email={user_email}")

        if not db:
            print("[habits_api GET] db is None")
            return jsonify({'success': True, 'habits': []}), 200

        try:
            docs = db.collection('habits').where('userID', '==', user_id).stream()
            habits = []

            for d in docs:
                h = d.to_dict() or {}
                h['id'] = d.id

                # Make createdAt safe for JSON / JS
                if 'createdAt' in h:
                    try:
                        v = h['createdAt']
                        if hasattr(v, 'isoformat'):
                            h['createdAt'] = v.isoformat()
                        elif hasattr(v, 'to_datetime'):
                            h['createdAt'] = v.to_datetime().isoformat()
                        else:
                            h['createdAt'] = str(v)
                    except Exception:
                        h['createdAt'] = str(h['createdAt'])

                habits.append(h)

            print(f"[habits_api GET] found {len(habits)} habits for user {user_id}")
            return jsonify({'success': True, 'habits': habits}), 200

        except Exception as e:
            print("[habits_api GET] error:", e)
            return jsonify({'success': False, 'error': 'Failed to fetch habits'}), 500

    # ---------- POST: create a new habit ---------- #
    # Accept JSON (from fetch) or form data
    data = request.get_json(silent=True) or request.form.to_dict(flat=True)

    if not db:
        return jsonify({'error': 'Database connection unavailable'}), 500

    try:
        habit = {
            'name': data.get('name'),
            'description': data.get('description', ''),
            'category': data.get('category', 'general'),
            'frequency': (data.get('frequency') or 'daily').lower(),
            'customFrequencyValue': data.get('customFrequencyValue'),
            'customFrequencyUnit': data.get('customFrequencyUnit'),
            'reminderEnabled': bool(data.get('reminderEnabled', False)),
            'reminderTime': data.get('reminderTime'),
            'reminderDays': data.get('reminderDays'),
            'userID': user_id,
            'createdAt': datetime.now(),
            'isActive': True,
            'isCompletedToday': False,
            'lastCompletedAt': None,
            'isPrivate': bool(data.get('isPrivate', False)),
            'currentStreak': 0,
            'longestStreak': 0,
            'completed_dates': [],
        }

        print(f"[habits_api POST] creating habit for user_id={user_id} -> {habit}")

        doc = db.collection('habits').document()
        doc.set(habit)


        print(f"[habits_api POST] created habit with id={doc.id}")
        return jsonify({'success': True,
                        'message': 'Habit created successfully!',
                        'habitId': doc.id}), 200

    except Exception as e:
        print("[habits_api POST] error:", e)
        return jsonify({'error': 'Failed to create habit'}), 500

# ---------------- Update Habit API ---------------- #
@app.route('/api/habits/<habit_id>', methods=['PUT'])
def update_habit(habit_id):
    """Update an existing habit"""
    print(f"[update_habit] Updating habit {habit_id}")
    
    # Must be logged in
    if 'user_email' not in session:
        return jsonify({'error': 'Authentication required'}), 401

    user_id = session.get('user_uid', session['user_email'])
    
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        # Validate required fields
        name = data.get('name', '').strip()
        if not name:
            return jsonify({'error': 'Habit name is required'}), 400
        
        if not db:
            return jsonify({'error': 'Database unavailable'}), 500
        
        # Check if habit exists and belongs to user
        habit_ref = db.collection('habits').document(habit_id)
        habit_doc = habit_ref.get()
        
        if not habit_doc.exists:
            return jsonify({'error': 'Habit not found'}), 404
        
        habit_data = habit_doc.to_dict() or {}
        if habit_data.get('userID') != user_id:
            return jsonify({'error': 'Not authorized to update this habit'}), 403
        
        # --- Normalize incoming fields from modal ---
        frequency = (data.get('frequency') or habit_data.get('frequency', 'daily')).lower()
        reminder_time = data.get('reminderTime')          # may be "" or null
        reminder_enabled = bool(data.get('reminderEnabled', False))
        is_private = bool(data.get('isPrivate', habit_data.get('isPrivate', False)))

        # --- Build update payload ---
        update_data = {
            'name': name,
            'description': data.get('description', '').strip(),
            'category': data.get('category', habit_data.get('category', 'General')),
            'frequency': frequency,
            'reminderEnabled': reminder_enabled,
            'reminderTime': reminder_time if reminder_time else None,
            'isPrivate': is_private,
            'updatedAt': datetime.now()
        }

        # Custom frequency support
        if frequency == 'custom':
            update_data['customFrequencyValue'] = data.get(
                'customFrequencyValue',
                habit_data.get('customFrequencyValue')
            )
            update_data['customFrequencyUnit'] = data.get(
                'customFrequencyUnit',
                habit_data.get('customFrequencyUnit', 'days')
            )
        else:
            update_data['customFrequencyValue'] = None
            update_data['customFrequencyUnit'] = None
        
        habit_ref.update(update_data)
        
        print(f"[update_habit] Successfully updated habit {habit_id}")
        return jsonify({'success': True, 'message': 'Habit updated successfully!'}), 200
        
    except Exception as e:
        print(f"[update_habit] Error updating habit {habit_id}: {e}")
        import traceback
        print(f"[update_habit] Traceback: {traceback.format_exc()}")
        return jsonify({'error': 'Failed to update habit'}), 500


# ---------------- Delete Habit API ---------------- #
@app.route('/api/habits/<habit_id>', methods=['DELETE'])
def delete_habit(habit_id):
    """Delete a habit and all its completions"""
    print(f"[delete_habit] Deleting habit {habit_id}")
    
    # Must be logged in
    if 'user_email' not in session:
        return jsonify({'error': 'Authentication required'}), 401

    user_id = session.get('user_uid', session['user_email'])
    
    try:
        if not db:
            return jsonify({'error': 'Database unavailable'}), 500
        
        # Check if habit exists and belongs to user
        habit_ref = db.collection('habits').document(habit_id)
        habit_doc = habit_ref.get()
        
        if not habit_doc.exists:
            return jsonify({'error': 'Habit not found'}), 404
        
        habit_data = habit_doc.to_dict()
        if habit_data.get('userID') != user_id:
            return jsonify({'error': 'Not authorized to delete this habit'}), 403
        
        # Delete all habit completions first
        completions_query = db.collection('habit_completions').where('habitID', '==', habit_id)
        completions_docs = completions_query.stream()
        
        for completion_doc in completions_docs:
            completion_doc.reference.delete()
            print(f"[delete_habit] Deleted completion {completion_doc.id}")
        
        # Delete the habit itself
        habit_ref.delete()
        
        print(f"[delete_habit] Successfully deleted habit {habit_id}")
        return jsonify({'success': True, 'message': 'Habit deleted successfully!'}), 200
        
    except Exception as e:
        print(f"[delete_habit] Error deleting habit {habit_id}: {e}")
        import traceback
        print(f"[delete_habit] Traceback: {traceback.format_exc()}")
        return jsonify({'error': 'Failed to delete habit'}), 500

# ---------------- Update Habit Streak API ---------------- #
@app.route('/update-habit-streak/<habit_id>', methods=['PUT'])
def update_habit_streak(habit_id):
    """Update a habit's current streak"""
    if 'user_email' not in session:
        return jsonify({'error': 'Authentication required'}), 401
    
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        current_streak = data.get('currentStreak')
        if current_streak is None:
            return jsonify({'error': 'currentStreak is required'}), 400
        
        # Automatically mark as completed if streak is 7 or more
        update_data = {
            'currentStreak': current_streak,
            'updatedAt': datetime.now()
        }
        
        # If streak reaches 7 or more, mark as completed
        if current_streak >= 7:
            update_data['status'] = 'Completed'
            update_data['lastCompleted'] = datetime.now()
        else:
            # If reducing streak below 7, mark as in progress
            update_data['status'] = 'In Progress'
        
        db.collection('habits').document(habit_id).update(update_data)
        return jsonify({'success': True}), 200
        
    except Exception as e:
        print("[update-habit-streak] error:", e)
        return jsonify({'error': 'Failed to update habit streak'}), 500

# ---------------- Habit Weekly Progress API ---------------- #
@app.route('/habit/<habit_id>/weekly-progress', methods=['GET'])
def get_habit_weekly_progress(habit_id):
    """Get weekly progress and streak data for a specific habit"""
    print(f"[get_habit_weekly_progress] Getting weekly progress for habit {habit_id}")
    
    # Must be logged in
    if 'user_email' not in session:
        return jsonify({'error': 'Authentication required'}), 401

    user_id = session.get('user_uid', session['user_email'])
    
    try:
        if not db:
            return jsonify({'error': 'Database unavailable'}), 500
        
        # Check if habit exists and belongs to user
        habit_ref = db.collection('habits').document(habit_id)
        habit_doc = habit_ref.get()
        
        if not habit_doc.exists:
            return jsonify({'error': 'Habit not found'}), 404
        
        habit_data = habit_doc.to_dict()
        if habit_data.get('userID') != user_id:
            return jsonify({'error': 'Not authorized to view this habit'}), 403
        
        # Get current streak from habit document
        current_streak = habit_data.get('currentStreak', 0)
        
        # Calculate weekly progress (last 7 days)
        end_date = datetime.now()
        start_date = end_date - timedelta(days=6)  # Last 7 days including today
        today = datetime.now().date()
        
        # Query habit completions for this week - get all and filter manually to avoid date comparison issues
        completions_query = db.collection('habit_completions').where('habitID', '==', habit_id)
        all_completions = list(completions_query.stream())
        
        # Filter for this week manually and check for today's completion
        weekly_count = 0
        completed_today = False
        for completion in all_completions:
            completion_data = completion.to_dict()
            if 'completedDate' in completion_data:
                completion_date = completion_data['completedDate']
                try:
                    # Handle Firestore Timestamp objects
                    if hasattr(completion_date, 'date'):
                        completion_date_obj = completion_date  # Already datetime
                    else:
                        # Convert timestamp to datetime if needed
                        completion_date_obj = completion_date.to_datetime() if hasattr(completion_date, 'to_datetime') else completion_date
                    
                    # Check if in this week
                    if start_date <= completion_date_obj <= end_date:
                        weekly_count += 1
                    
                    # Check if completed today
                    if hasattr(completion_date_obj, 'date'):
                        if completion_date_obj.date() == today:
                            completed_today = True
                except Exception as date_error:
                    print(f"[get_habit_weekly_progress] Date processing error: {date_error}")
                    # Skip this completion if we can't process the date
                    continue
        
        # For testing: if no completions, use current_streak as test data
        if weekly_count == 0 and current_streak > 0:
            weekly_count = min(current_streak, 7)  # Show some progress based on streak
        
        # For now, use current streak as longest streak to avoid complexity
        # TODO: Implement proper longest streak calculation later
        longest_streak = current_streak
        
        # Check if habit is marked as completed (like goals)
        habit_status = habit_data.get('status', 'In Progress')
        is_completed = habit_status == 'Completed' or completed_today
        
        # If status is Completed, show 7/7 progress (100%)
        if habit_status == 'Completed':
            weekly_count = 7
        
        print(f"[get_habit_weekly_progress] Habit {habit_id}: weekly_count={weekly_count}, current_streak={current_streak}, longest_streak={longest_streak}, completed_today={completed_today}, status={habit_status}, is_completed={is_completed}")
        
        return jsonify({
            'success': True,
            'weekly_count': weekly_count,
            'streak_current': current_streak,
            'streak_longest': longest_streak,
            'completed_today': is_completed,  # Send overall completion state
            'status': habit_status
        }), 200
        
    except Exception as e:
        print(f"[get_habit_weekly_progress] Error getting weekly progress for habit {habit_id}: {e}")
        import traceback
        print(f"[get_habit_weekly_progress] Traceback: {traceback.format_exc()}")
        return jsonify({'error': 'Failed to get habit weekly progress'}), 500

# ---------------- Mark Habit Complete API ---------------- #
@app.route('/habit/<habit_id>/complete', methods=['POST'])
def mark_habit_complete(habit_id):
    """Mark a habit as complete for today"""
    print(f"[mark_habit_complete] Marking habit {habit_id} as complete")
    
    # Must be logged in
    if 'user_email' not in session:
        return jsonify({'error': 'Authentication required'}), 401

    user_id = session.get('user_uid', session['user_email'])

    try:
        if not db:
            return jsonify({'error': 'Database unavailable'}), 500
        
        # Check if habit exists and belongs to user
        habit_ref = db.collection('habits').document(habit_id)
        habit_doc = habit_ref.get()
        
        if not habit_doc.exists:
            return jsonify({'error': 'Habit not found'}), 404
        
        habit_data = habit_doc.to_dict()
        if habit_data.get('userID') != user_id:
            return jsonify({'error': 'Not authorized to complete this habit'}), 403
        
        # Check if already completed (check status field like goals)
        habit_status = habit_data.get('status', 'In Progress')
        if habit_status == 'Completed':
            print(f"[mark_habit_complete] Habit {habit_id} already marked as complete")
            return jsonify({'success': True, 'message': 'Already completed'}), 200
        
        # Mark habit as complete - just update the status field like goals
        # No need to create multiple completion records
        from datetime import datetime
        
        # Get or maintain current streak
        current_streak = habit_data.get('currentStreak', 0)
        # When marking complete, ensure minimum streak of 7 days
        if current_streak < 7:
            current_streak = 7
            
        # Single write operation to mark as completed
        habit_ref.update({
            'currentStreak': current_streak,
            'lastCompleted': datetime.now(),
            'updatedAt': datetime.now(),
            'status': 'Completed'  # Mark as completed like goals
        })
        
        print(f"[mark_habit_complete] Successfully marked habit {habit_id} as complete with status=Completed, streak: {current_streak}")
        return jsonify({
            'success': True, 
            'message': 'Habit marked as complete!',
            'newStreak': current_streak
        }), 200
        
    except Exception as e:
        print(f'[mark_habit_complete] error: {e}')
        import traceback
        print(f"[mark_habit_complete] Traceback: {traceback.format_exc()}")
        return jsonify(success=False, error="Failed to mark habit complete"), 500


# ---------------- Reopen Habit API ---------------- #
@app.route('/habit/<habit_id>/reopen', methods=['POST'])
def reopen_habit(habit_id):
    """Reopen a habit by removing today's completion"""
    print(f"[reopen_habit] Reopening habit {habit_id}")
    
    # Must be logged in
    if 'user_email' not in session:
        return jsonify({'error': 'Authentication required'}), 401

    user_id = session.get('user_uid', session['user_email'])
    
    try:
        if not db:
            return jsonify({'error': 'Database unavailable'}), 500
        
        # Check if habit exists and belongs to user
        habit_ref = db.collection('habits').document(habit_id)
        habit_doc = habit_ref.get()
        
        if not habit_doc.exists:
            return jsonify({'error': 'Habit not found'}), 404
        
        habit_data = habit_doc.to_dict()
        if habit_data.get('userID') != user_id:
            return jsonify({'error': 'Not authorized to reopen this habit'}), 403
        
        # Delete ALL completions for this habit to reset progress to 0/7
        # This makes reopen work like goals - reopen = reset to zero
        from datetime import datetime, date
        
        # Query for all completions for this habit
        all_completions = db.collection('habit_completions').where('habitID', '==', habit_id).where('userID', '==', user_id).stream()
        
        deleted_count = 0
        for completion in all_completions:
            completion.reference.delete()
            deleted_count += 1
        
        print(f"[reopen_habit] Deleted {deleted_count} completions for habit {habit_id}")
        
        # Reset habit's current streak to 0
        current_streak = 0
        habit_ref.update({
            'currentStreak': current_streak,
            'updatedAt': datetime.now(),
            'status': 'In Progress'  # Reset status like goals
        })
        
        print(f"[reopen_habit] Successfully reopened habit {habit_id}, new streak: {current_streak}")
        return jsonify({
            'success': True, 
            'message': 'Habit reopened successfully!',
            'newStreak': current_streak
        }), 200
        
    except Exception as e:
        print(f"[reopen_habit] Error reopening habit {habit_id}: {e}")
        import traceback
        print(f"[reopen_habit] Traceback: {traceback.format_exc()}")
        return jsonify({'error': 'Failed to reopen habit'}), 500

# ---------------- Reset All Habits Today API ---------------- #
@app.route('/reset-habits-today', methods=['PUT'])
def reset_habits_today():
    """Reset all user's habits by deleting all completions and resetting streaks to 0"""
    print("[reset_habits_today] Resetting all habits for today")
    
    # Must be logged in
    if 'user_email' not in session:
        return jsonify({'error': 'Authentication required'}), 401

    user_id = session.get('user_uid', session['user_email'])
    
    try:
        if not db:
            return jsonify({'error': 'Database unavailable'}), 500
        
        # Get all user's habits
        habits_query = db.collection('habits').where('userID', '==', user_id)
        user_habits = list(habits_query.stream())
        
        reset_count = 0
        for habit_doc in user_habits:
            habit_id = habit_doc.id
            
            # Delete ALL completions for this habit
            all_completions = db.collection('habit_completions').where('habitID', '==', habit_id).where('userID', '==', user_id).stream()
            
            for completion in all_completions:
                completion.reference.delete()
            
            # Reset habit's current streak to 0 and set status to In Progress
            habit_doc.reference.update({
                'currentStreak': 0,
                'updatedAt': datetime.now(),
                'status': 'In Progress'
            })
            
            reset_count += 1
        
        print(f"[reset_habits_today] Successfully reset {reset_count} habits")
        return jsonify({
            'success': True, 
            'message': f'Reset {reset_count} habits successfully!',
            'reset_count': reset_count
        }), 200
        
    except Exception as e:
        print(f"[reset_habits_today] Error resetting habits: {e}")
        import traceback
        print(f"[reset_habits_today] Traceback: {traceback.format_exc()}")
        return jsonify({'success': False, 'error': 'Failed to reset habits'}), 500

# ---------------- Journal page ---------------- #
@app.route('/journal', methods=['GET', 'POST'], endpoint='journal_page')
def journal_page():
    auth_result = require_auth()
    if not isinstance(auth_result, tuple):
        return auth_result
    user_email, user_uid = auth_result

    # POST: create a journal entry
    if request.method == 'POST':
        data = request.get_json(silent=True) or request.form
        content = (data.get('entry') or data.get('content') or '').strip()
        if not content:
            return jsonify({'error': 'Entry cannot be empty'}), 400

        if not db:
            return jsonify({'error': 'Database unavailable'}), 500

        try:
            doc_ref = db.collection('journal_entries').document()
            doc_ref.set({
                'userID': user_uid,
                'email': user_email,
                'content': content,
                'createdAt': datetime.now(),
            })
            return jsonify({'success': True, 'id': doc_ref.id}), 200
        except Exception as e:
            print('[journal_page POST] Firestore error:', e)
            return jsonify({'error': 'Failed to save entry'}), 500

    # GET: fetch recent entries WITHOUT Firestore order_by (no index required)
    entries = []
    if db:
        try:
            docs = db.collection('journal_entries').where('userID', '==', user_uid).stream()
            temp = []
            for d in docs:
                item = d.to_dict() or {}
                item['id'] = d.id
                temp.append(item)
            # Sort locally by createdAt desc, then take top 10
            entries = sorted(
                temp,
                key=lambda x: x.get('createdAt') or datetime.min,
                reverse=True
            )[:10]
        except Exception as e:
            print('[journal_page GET] Firestore read error:', e)

    return render_template(
        'journal.html',
        entries=entries,
        active_tab='journal',
        user_email=user_email,
        user_uid=user_uid
    )
# ---------------- Journal History ---------------- #
@app.route('/journal/history', endpoint='journal_history')
def journal_history():
    auth_result = require_auth()
    if not isinstance(auth_result, tuple):
        return auth_result
    user_email, user_uid = auth_result

    print("[journal_history] user_email =", user_email, "user_uid =", user_uid)

    entries = []
    if db:
        try:
            # 🔍 Try to fetch only this user's entries
            docs = db.collection('journal_entries').where('userID', '==', user_uid).stream()

            temp = []
            raw_count = 0
            for d in docs:
                data = d.to_dict() or {}
                raw_count += 1
                item = {
                    "id": d.id,
                    "content": data.get("content", ""),
                    "createdAt": data.get("createdAt"),
                    "updatedAt": data.get("updatedAt"),
                }
                temp.append(item)

            print(f"[journal_history] Firestore docs for this user: {raw_count}")

            # Sort newest → oldest
            from datetime import datetime as _dt
            entries = sorted(
                temp,
                key=lambda x: x.get("createdAt") or _dt.min,
                reverse=True
            )

            # Convert timestamps to strings for template
            for e in entries:
                e["createdAt"] = _ts_to_iso(e["createdAt"])
                e["updatedAt"] = _ts_to_iso(e["updatedAt"])

        except Exception as e:
            print("[journal_history] Firestore read error:", e)

    return render_template(
        'journal_history.html',
        entries=entries,
        active_tab='journal',
        user_email=user_email,
        user_uid=user_uid
    )

# ---------------- Edit Journal Entry (simplified) ---------------- #
@app.route('/journal/<entry_id>/edit', methods=['GET', 'POST'], endpoint='edit_journal')
def edit_journal(entry_id):
    auth_result = require_auth()
    if not isinstance(auth_result, tuple):
        return auth_result
    user_email, user_uid = auth_result

    if not db:
        flash("Database unavailable", "error")
        return redirect(url_for('journal_history'))

    doc_ref = db.collection('journal_entries').document(entry_id)

    # Try to load the document once, reuse it for GET/POST
    try:
        snap = doc_ref.get()
        if not snap.exists:
            print("[edit_journal] entry not found:", entry_id)
            flash("Journal entry not found", "error")
            return redirect(url_for('journal_history'))
        data = snap.to_dict() or {}
    except Exception as e:
        print("[edit_journal] Firestore read error:", e)
        flash("Failed to load journal entry", "error")
        return redirect(url_for('journal_history'))

    # ---------- POST: save changes ---------- #
    if request.method == 'POST':
        content = (request.form.get('content') or '').strip()
        if not content:
            flash("Entry cannot be empty", "error")
            return redirect(url_for('edit_journal', entry_id=entry_id))

        try:
            doc_ref.update({
                'content': content,
                'updatedAt': datetime.now()
            })
            print("[edit_journal POST] updated entry:", entry_id)
            flash("Journal entry updated successfully", "success")
        except Exception as e:
            print("[edit_journal POST] update error:", e)
            flash("Failed to update journal entry", "error")

        return redirect(url_for('journal_history'))

        # ---------- GET: render edit page ---------- #
    entry = {
        "id": entry_id,
        "content": data.get("content", ""),
        "createdAt": _ts_to_iso(data.get("createdAt")),
        "updatedAt": _ts_to_iso(data.get("updatedAt")),
    }

    return render_template(
        'edit_journal.html',
        entry=entry,
        active_tab='journal',
        user_email=user_email,
        user_uid=user_uid
    )



# ---- DEV ONLY: quick session setter for curl (remove later) ----
@app.route('/_dev/set-session')
def _dev_set_session():
    session['user_email'] = 'test@gmail.com'
    session['user_uid'] = 'localdev'
    return 'ok', 200




# ---------------- Debug helpers ---------------- #
@app.route('/debug-session')
def debug_session():
    return jsonify({
        'authenticated': 'user_email' in session,
        'session_data': dict(session),
        'user_email': session.get('user_email'),
        'user_uid': session.get('user_uid'),
    })

@app.route('/_debug/routes')
def _debug_routes():
    return {'endpoints': sorted(list(dict(app.view_functions).keys()))}

@app.route('/_debug/create_users')
def _debug_create_users():
    """Create missing user documents"""
    try:
        from datetime import datetime
        
        # Create current user document
        current_user_uid = 'vHnWe25ZIVZcU393NarCAdQUVCl2'
        current_user_data = {
            'uid': current_user_uid,
            'email': 'swarheka@stevens.edu',
            'displayName': 'Swarhekar',
            'friends': [],
            'friendRequests': {'incoming': [], 'outgoing': []},
            'stats': {'currentStreak': 0, 'longestStreak': 0, 'totalHabitsCompleted': 0},
            'createdAt': datetime.now(),
            'lastLoginAt': datetime.now()
        }
        
        db.collection('users').document(current_user_uid).set(current_user_data)
        
        # Create arundhati user document  
        arundhati_uid = 'arundhati_uid_123'
        arundhati_data = {
            'uid': arundhati_uid,
            'email': 'arundhati059@gmail.com',
            'displayName': 'Arundhati',
            'friends': [],
            'friendRequests': {'incoming': [], 'outgoing': []},
            'stats': {'currentStreak': 5, 'longestStreak': 10, 'totalHabitsCompleted': 25},
            'createdAt': datetime.now(),
            'lastLoginAt': datetime.now()
        }
        
        db.collection('users').document(arundhati_uid).set(arundhati_data)
        
        # Create user documents for all Firebase Auth users who don't have Firestore docs
        auth_users = auth.list_users().users
        created_count = 0
        
        for auth_user in auth_users:
            user_doc = db.collection('users').document(auth_user.uid).get()
            if not user_doc.exists:
                user_data = {
                    'uid': auth_user.uid,
                    'email': auth_user.email,
                    'displayName': auth_user.display_name or 'User',
                    'friends': [],
                    'friendRequests': {'incoming': [], 'outgoing': []},
                    'stats': {'currentStreak': 0, 'longestStreak': 0, 'totalHabitsCompleted': 0},
                    'createdAt': datetime.now(),
                    'lastLoginAt': datetime.now()
                }
                db.collection('users').document(auth_user.uid).set(user_data)
                created_count += 1
        
        return {
            'success': True, 
            'message': f'Created {created_count} user documents from Firebase Auth',
            'total_auth_users': len(auth_users),
            'created_count': created_count
        }
        
    except Exception as e:
        return {'success': False, 'error': str(e)}

# ---------------- Run ---------------- #
if __name__ == '__main__':
    # host/port visible to your curl and browser
    app.run(debug=True, host='127.0.0.1', port=5000)
