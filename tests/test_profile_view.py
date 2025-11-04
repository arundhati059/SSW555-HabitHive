import os
import json
import pytest
from datetime import datetime
from HabitHive import AuthManager, ProfileManager, load_users, save_users, DATA_FILE

# ---------- FIXTURES ----------
@pytest.fixture(autouse=True)
def clear_users_json():
    """Reset the users.json file before each test."""
    if os.path.exists(DATA_FILE):
        os.remove(DATA_FILE)
    save_users([])


# ---------- UNIT TESTS ----------

def test_sign_up_creates_user():
    success, msg = AuthManager.sign_up("test@example.com", "securepass")
    assert success is True
    assert "User created successfully" in msg
    users = load_users()
    assert len(users) == 1
    assert users[0]["email"] == "test@example.com"


def test_sign_up_duplicate_email():
    AuthManager.sign_up("dup@example.com", "securepass")
    success, msg = AuthManager.sign_up("dup@example.com", "securepass")
    assert success is False
    assert "Email already registered" in msg


def test_login_valid_user():
    AuthManager.sign_up("login@example.com", "securepass")
    success, msg = AuthManager.login("login@example.com", "securepass")
    assert success is True
    assert "Welcome back" in msg


def test_login_invalid_password():
    AuthManager.sign_up("login2@example.com", "securepass")
    success, msg = AuthManager.login("login2@example.com", "wrongpass")
    assert success is False
    assert "Incorrect password" in msg


# ---------- PROFILE TESTS ----------

def test_create_profile_valid_user(tmp_path):
    AuthManager.sign_up("profile@example.com", "securepass")
    avatar = tmp_path / "avatar.png"
    avatar.write_text("fakeimage")

    success, msg = ProfileManager.create_profile(
        email="profile@example.com",
        first_name="John",
        last_name="Doe",
        display_name="JD",
        avatar_path=str(avatar)
    )

    assert success is True
    assert "Profile created successfully" in msg

    users = load_users()
    assert users[0]["profile"]["display_name"] == "JD"
    assert os.path.exists(users[0]["profile"]["avatar"])


def test_view_profile_no_profile():
    AuthManager.sign_up("noprof@example.com", "securepass")
    success, msg = ProfileManager.view_profile("noprof@example.com")
    assert success is False
    assert "No profile created yet" in msg


def test_invalid_email_signup():
    success, msg = AuthManager.sign_up("invalidemail", "password")
    assert success is False
    assert "Invalid email format" in msg
