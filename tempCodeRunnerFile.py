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
    """
    print("🔐 /verify-token called")
    try:
        data = request.get_json(silent=True) or {}
        id_token = data.get('idToken')
        if not id_token:
            return jsonify({'error': 'No ID token provided'}), 400

        decoded = auth.verify_id_token(id_token)
        session['user_email'] = decoded['email']
        session['user_uid'] = decoded['uid']
        print(f"✅ Token verified for {decoded['email']} ({decoded['uid']})")
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

@app.route('/analytics', endpoint='analytics_page')
def analytics_page():
    auth_result = require_auth()
    if not isinstance(auth_result, tuple):
        return auth_result
    user_email, user_uid = auth_result
    return render_template('analytics.html',
                           user_email=user_email,
                           user_uid=user_uid,
                           active_tab='analytics')

@app.route('/friends', endpoint='friends_page')
def friends_page():
    auth_result = require_auth()
    if not isinstance(auth_result, tuple):
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

# ---------------- Profile ---------------- #
@app.route('/profile', endpoint='profile_page')
def profile_page():
    auth_result = require_auth()
    if not isinstance(auth_result, tuple):
        return auth_result
    user_email, user_uid = auth_result

    profile = {
        "username": (user_email or "user").split('@')[0],
        "email": user_email or "",
        "first_name": "John",
        "last_name": "Doe",
        "display_name": "",
        "avatar": "https://via.placeholder.com/120",
        "member_since": "—"
    }

    # Load profile details if present
    if db:
        try:
            doc = db.collection("profiles").document(user_email).get()
            if doc.exists:
                data = doc.to_dict() or {}
                profile.update({
                    "first_name": data.get("first_name", profile["first_name"]),
                    "last_name": data.get("last_name", profile["last_name"]),
                    "display_name": data.get("display_name", profile["display_name"]),
                    "avatar": data.get("avatar_url", profile["avatar"]),
                    "member_since": data.get("created_at", profile["member_since"]),
                    "username": data.get("display_name", profile["username"]) or profile["username"],
                })
        except Exception as e:
            print("[profile_page] Firestore read error:", e)

    # Stats: habits count & journal count
    stats = {"active_habits": 0, "journal_entries": 0}
    try:
        if db:
            # habits
            hcount = 0
            for _ in db.collection('habits').where('userID', '==', user_uid).stream():
                hcount += 1
            stats['active_habits'] = hcount

            # journals
            jcount = 0
            for _ in db.collection('journal_entries').where('userID', '==', user_uid).stream():
                jcount += 1
            stats['journal_entries'] = jcount
    except Exception as e:
        print("[profile_page] counting error:", e)

    # Recent active habits
    recent_habits = []
    try:
        if db:
            q = db.collection('habits').where('userID', '==', user_uid).limit(5)
            for d in q.stream():
                h = d.to_dict()
                recent_habits.append({
                    "name": h.get('name') or 'Habit',
                    "frequency": h.get('frequency', '').title()
                })
    except Exception as e:
        print("[profile_page] recent habits error:", e)

    return render_template('profile.html',
                           profile=profile,
                           stats=stats,
                           recent_habits=recent_habits,
                           active_tab='profile')

@app.route('/edit-profile', methods=['GET', 'POST'], endpoint='edit_profile')
def edit_profile():
    auth_result = require_auth()
    if not isinstance(auth_result, tuple):
        return auth_result
    email, uid = auth_result

    # defaults
    profile_data = {
        "username": email.split('@')[0],
        "email": email,
        "first_name": "",
        "last_name": "",
        "display_name": "",
        "avatar": "https://via.placeholder.com/120",
        "member_since": ""
    }

    # prefill
    if db:
        try:
            doc = db.collection("profiles").document(email).get()
            if doc.exists:
                data = doc.to_dict() or {}
                profile_data.update({
                    "first_name": data.get("first_name", ""),
                    "last_name": data.get("last_name", ""),
                    "display_name": data.get("display_name", ""),
                    "avatar": data.get("avatar_url", profile_data["avatar"]),
                    "member_since": data.get("created_at", ""),
                })
        except Exception as e:
            print("[edit_profile GET] Firestore read error:", e)

    if request.method == 'POST':
        first_name = (request.form.get('first_name') or '').strip()
        last_name  = (request.form.get('last_name') or '').strip()
        display    = (request.form.get('display_name') or '').strip()
        avatar_file = request.files.get('avatar')

        update_fields = {
            "first_name": first_name,
            "last_name": last_name,
            "display_name": display,
            "updated_at": datetime.now()
        }

        # optional avatar upload
        try:
            if avatar_file and avatar_file.filename:
                bucket = storage.bucket()
                key = f"users/avatars/{uid}/{secure_filename(f'{uid}_{int(datetime.now().timestamp())}')}"
                blob = bucket.blob(key)
                blob.upload_from_file(avatar_file, content_type=avatar_file.mimetype or "image/png")
                blob.patch()
                avatar_url = blob.generate_signed_url(version="v4", expiration=timedelta(days=7), method="GET")
                update_fields["avatar_path"] = key
                update_fields["avatar_url"] = avatar_url
        except Exception as e:
            print("[edit_profile POST] Avatar upload skipped/error:", e)

        try:
            if db:
                db.collection("profiles").document(email).set(update_fields, merge=True)
                flash("Profile updated successfully", "success")
            else:
                flash("Database unavailable; could not save profile", "error")
        except Exception as e:
            print("[edit_profile POST] Firestore write error:", e)
            flash("Failed to update profile", "error")

        return redirect(url_for('profile_page'))

    return render_template('edit_profile.html',
                           profile=profile_data,
                           user_email=email,
                           user_uid=uid,
                           active_tab='profile')

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

# ---------------- Habits API ---------------- #
@app.route('/api/habits', methods=['GET','POST'])
def habits_api():
    if 'user_email' not in session:
        return jsonify({'error': 'Authentication required'}), 401
    user_id = session.get('user_uid', session['user_email'])

    if request.method == 'GET':
        if not db: return jsonify({'success': True, 'habits': []}), 200
        try:
            docs = db.collection('habits').where('userID','==',user_id).stream()
            habits = []
            for d in docs:
                h = d.to_dict(); h['id'] = d.id
                habits.append(h)
            return jsonify({'success': True, 'habits': habits}), 200
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    # POST create
    data = request.get_json(silent=True) or request.form.to_dict(flat=True)
    if not db: return jsonify({'error': 'Database connection unavailable'}), 500
    try:
        habit = {
            'name': data.get('name'),
            'description': data.get('description',''),
            'category': data.get('category','general'),
            'frequency': (data.get('frequency') or 'daily').lower(),
            'customFrequencyValue': data.get('customFrequencyValue'),
            'customFrequencyUnit': data.get('customFrequencyUnit'),
            'reminderEnabled': bool(data.get('reminderEnabled', False)),
            'reminderTime': data.get('reminderTime'),
            'reminderDays': data.get('reminderDays'),
            'userID': user_id,
            'createdAt': datetime.now(),
            'isActive': True
        }
        doc = db.collection('habits').document()
        doc.set(habit)
        return jsonify({'success': True, 'message': 'Habit created successfully!', 'habitId': doc.id}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ---------------- Journal APIs (copy-paste starts) ----------------
from datetime import datetime
from firebase_admin import firestore as _fs
from flask import jsonify, request, session

def _ts_to_iso(v):
    """Safely stringify Firestore Timestamp/datetime for JSON."""
    try:
        if hasattr(v, "isoformat"):
            return v.isoformat()
        if hasattr(v, "to_datetime"):
            return v.to_datetime().isoformat()
    except Exception:
        pass
    return str(v) if v is not None else None


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

# ---------------- Run ---------------- #
if __name__ == '__main__':
    # host/port visible to your curl and browser
    app.run(debug=True, host='127.0.0.1', port=5000)
