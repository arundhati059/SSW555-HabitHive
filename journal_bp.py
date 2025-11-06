# journal_bp.py
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from datetime import datetime

# Use the already-initialized Firebase Admin app; this won't re-init if it's set up in web_app.py
try:
    import firebase_admin  # noqa: F401
    from firebase_admin import firestore
    db = firestore.client()
except Exception:
    db = None

journal_bp = Blueprint("journal", __name__, template_folder="templates")

def _require_auth():
    """Local minimal auth check to avoid importing from web_app (no circular imports)."""
    if "user_email" not in session:
        return None, None, jsonify({"error": "Please log in"}), 401
    user_email = session["user_email"]
    user_uid = session.get("user_uid", "temp_uid_" + user_email.replace("@", "_").replace(".", "_"))
    if "user_uid" not in session:
        session["user_uid"] = user_uid
    return user_email, user_uid, None, None

@journal_bp.route("/journal", methods=["GET", "POST"])
@journal_bp.route("/journal/create", methods=["GET", "POST"])
def journal_page():
    """
    Create a journal entry.
    - GET: show a form with a dropdown of the user's active habits.
    - POST: save the entry to Firestore (collection 'journal_entries').
    """
    user_email, user_uid, err_resp, err_code = _require_auth()
    if err_resp:
        # If the request is from the browser, redirect to login page name used in your app
        if request.method == "GET":
            return redirect(url_for("login"))
        return err_resp, err_code

    if request.method == "POST":
        if not db:
            return jsonify({"error": "Database connection unavailable"}), 500

        # Support both form-POST (from the page) and JSON POST (from fetch/AJAX)
        payload = request.get_json(silent=True) or {}
        habit_id = request.form.get("habit_id") or payload.get("habit_id")
        text = request.form.get("text") or payload.get("text")
        mood = (request.form.get("mood") or payload.get("mood") or "").strip()

        if not habit_id or not text:
            msg = "habit_id and text are required"
            if payload:
                return jsonify({"error": msg}), 400
            flash(msg, "error")
            return redirect(url_for("journal.journal_page"))

        entry = {
            "userID": user_uid,
            "habitID": habit_id,
            "text": text.strip(),
            "mood": mood,
            "createdAt": datetime.now(),
        }

        try:
            doc_ref = db.collection("journal_entries").document()
            doc_ref.set(entry)
            if request.is_json:
                return jsonify({"success": True, "entryId": doc_ref.id}), 201
            flash("Journal entry saved", "success")
            # Send them somewhere useful in your app:
            return redirect(url_for("dashboard") if "dashboard" in journal_bp.app.view_functions else url_for("profile_page"))
        except Exception as e:
            if request.is_json:
                return jsonify({"error": str(e)}), 500
            flash(f"Could not save journal: {e}", "error")

    # GET: build dropdown of active habits for this user
    habits = []
    if db:
        try:
            # your habits use fields: userID + isActive True
            qs = (db.collection("habits")
                    .where("userID", "==", user_uid)
                    .where("isActive", "==", True)
                    .stream())
            for h in qs:
                hd = h.to_dict()
                hd["id"] = h.id
                habits.append(hd)
        except Exception as e:
            # Don't crash the page if listing fails
            print(f"[journal] error loading habits: {e}")

    return render_template("journal.html", habits=habits, active_tab="journal")
