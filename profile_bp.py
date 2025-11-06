# profile_bp.py
from flask import Blueprint, render_template, redirect, url_for, session, jsonify
from datetime import datetime
from typing import Dict, Any

# Reuse the Firebase Admin app that web_app.py already initialized
try:
    import firebase_admin  # noqa: F401
    from firebase_admin import firestore
    db = firestore.client()
except Exception:
    db = None

profile_bp = Blueprint("profile", __name__, template_folder="templates")


def _require_auth():
    """Local auth check (avoid import cycles with web_app)."""
    if "user_email" not in session:
        return None, None, jsonify({"error": "Please log in"}), 401
    email = session["user_email"]
    uid = session.get("user_uid", "temp_uid_" + email.replace("@", "_").replace(".", "_"))
    if "user_uid" not in session:
        session["user_uid"] = uid
    return email, uid, None, None


def _fmt_member_since(value) -> str:
    """Render Firestore timestamp / datetime / str into 'Month YYYY'."""
    try:
        # Firestore Timestamp has .to_datetime()
        if hasattr(value, "to_datetime"):
            value = value.to_datetime()
        if isinstance(value, datetime):
            return value.strftime("%B %Y")
        if isinstance(value, str) and value:
            # try ISO-ish inputs
            try:
                dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
                return dt.strftime("%B %Y")
            except Exception:
                return value
    except Exception:
        pass
    return "—"


@profile_bp.route("/profile", methods=["GET"])
def profile_page():
    """View Profile (read-only). Shows basic info + small stats."""
    email, uid, err_resp, err_code = _require_auth()
    if err_resp:
        # Browser request? send to login page name used in your app.
        return redirect(url_for("login"))

    # Defaults (safe if Firestore is down)
    profile: Dict[str, Any] = {
        "username": email.split("@")[0],
        "email": email,
        "first_name": "John",
        "last_name": "Doe",
        "avatar": "https://via.placeholder.com/120",
        "member_since": "—",
    }
    stats = {"active_habits": 0, "journal_entries": 0}
    recent_habits = []

    if db:
        try:
            # Pull user profile (document id = user_email)
            doc = db.collection("profiles").document(email).get()
            if doc.exists:
                data = doc.to_dict() or {}
                profile["first_name"] = data.get("first_name", profile["first_name"])
                profile["last_name"] = data.get("last_name", profile["last_name"])
                profile["avatar"] = data.get("avatar_url", profile["avatar"])
                profile["member_since"] = _fmt_member_since(
                    data.get("created_at", profile["member_since"])
                )

            # Count active habits
            h_docs = (
                db.collection("habits")
                .where("userID", "==", uid)
                .where("isActive", "==", True)
                .stream()
            )
            h_list = []
            for h in h_docs:
                item = h.to_dict()
                item["id"] = h.id
                h_list.append(item)
            stats["active_habits"] = len(h_list)
            recent_habits = h_list[:5]

            # Count journal entries
            j_docs = (
                db.collection("journal_entries")
                .where("userID", "==", uid)
                .stream()
            )
            stats["journal_entries"] = sum(1 for _ in j_docs)

        except Exception as e:
            # Do not crash page; show what we have
            print(f"[profile] Firestore fetch error: {e}")

    return render_template(
        "profile.html",
        profile=profile,
        stats=stats,
        recent_habits=recent_habits,
        active_tab="profile",
    )
