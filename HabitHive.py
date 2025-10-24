import os
import re
import json
from datetime import datetime
from getpass import getpass

# ------------------------------
# DATA STORAGE FILE
# ------------------------------
DATA_FILE = "users.json"
AVATAR_DIR = "avatars"

# Create folders if not exist
os.makedirs(AVATAR_DIR, exist_ok=True)

# ------------------------------
# HELPER FUNCTIONS
# ------------------------------
def load_users():
    """Load users from JSON file."""
    if not os.path.exists(DATA_FILE):
        return []
    with open(DATA_FILE, "r") as f:
        return json.load(f)

def save_users(users):
    """Save users back to JSON file."""
    with open(DATA_FILE, "w") as f:
        json.dump(users, f, indent=4)

def find_user(email):
    """Find user by email."""
    users = load_users()
    for user in users:
        if user["email"].lower() == email.lower():
            return user
    return None


# ------------------------------
# AUTHENTICATION MANAGER
# ------------------------------
class AuthManager:
    """Handles local user sign-up and login."""

    @staticmethod
    def validate_email(email):
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))

    @staticmethod
    def validate_password(password):
        if len(password) < 6:
            return False, "Password must be at least 6 characters long"
        return True, "Password is valid"

    @staticmethod
    def sign_up(email, password):
        if not AuthManager.validate_email(email):
            return False, "Invalid email format"

        password_valid, msg = AuthManager.validate_password(password)
        if not password_valid:
            return False, msg

        users = load_users()
        if any(u["email"].lower() == email.lower() for u in users):
            return False, "Email already registered."

        new_user = {
            "email": email,
            "password": password,
            "created_at": str(datetime.now()),
            "profile": None
        }
        users.append(new_user)
        save_users(users)
        return True, f"User created successfully with email: {email}"

    @staticmethod
    def login(email, password):
        user = find_user(email)
        if not user:
            return False, "User not found."
        if user["password"] != password:
            return False, "Incorrect password."
        return True, f"Welcome back, {email}!"


# ------------------------------
# PROFILE MANAGER
# ------------------------------
class ProfileManager:
    """Handles user profile creation and viewing locally."""

    @staticmethod
    def create_profile(email, first_name, last_name, display_name, avatar_path=None):
        user = find_user(email)
        if not user:
            return False, f"No user found with email: {email}. Please sign up first."

        # Validate fields
        if not first_name.strip():
            return False, "First name cannot be empty."
        if not last_name.strip():
            return False, "Last name cannot be empty."
        if not display_name.strip():
            display_name = f"{first_name} {last_name}"

        # Handle avatar upload
        avatar_file = None
        if avatar_path and os.path.exists(avatar_path):
            ext = os.path.splitext(avatar_path)[1]
            avatar_file = os.path.join(AVATAR_DIR, f"{first_name.lower()}_{last_name.lower()}{ext}")
            with open(avatar_path, "rb") as src, open(avatar_file, "wb") as dest:
                dest.write(src.read())
        else:
            avatar_file = "avatars/default.png"

        # Update profile
        users = load_users()
        for u in users:
            if u["email"].lower() == email.lower():
                u["profile"] = {
                    "first_name": first_name,
                    "last_name": last_name,
                    "display_name": display_name,
                    "email": email,
                    "avatar": avatar_file,
                    "updated_at": str(datetime.now())
                }
                save_users(users)
                return True, f"Profile created successfully for {display_name}"

        return False, "Failed to update profile."

    @staticmethod
    def view_profile(email):
        user = find_user(email)
        if not user:
            return False, "User not found."
        if not user.get("profile"):
            return False, "No profile created yet."
        return True, user["profile"]


# ------------------------------
# MAIN APP FLOW
# ------------------------------
def get_input(prompt):
    return input(prompt)


def main():
    print("\n🌱 Welcome to HabitHive!")
    print("Your personal habit-tracking and profile management app 🐝")

    while True:
        print("\nChoose an option:")
        print("1️⃣ Sign Up")
        print("2️⃣ Log In")
        print("3️⃣ Create Profile")
        print("4️⃣ View Profile")
        print("5️⃣ Exit")

        choice = get_input("Enter choice (1–5): ").strip()

        if choice == "1":
            email = get_input("Enter email: ")
            password = getpass("Enter password (hidden): ")
            success, msg = AuthManager.sign_up(email, password)
            print(f"\n{'✅' if success else '❌'} {msg}")

        elif choice == "2":
            email = get_input("Enter email: ")
            password = getpass("Enter password (hidden): ")
            success, msg = AuthManager.login(email, password)
            print(f"\n{'✅' if success else '❌'} {msg}")

        elif choice == "3":
            email = get_input("Enter your registered email: ")
            first = get_input("Enter first name: ")
            last = get_input("Enter last name: ")
            display = get_input("Enter display name: ")
            avatar_path = get_input("Enter avatar image path (optional): ")
            success, msg = ProfileManager.create_profile(email, first, last, display, avatar_path or None)
            print(f"\n{'✅' if success else '❌'} {msg}")

        elif choice == "4":
            email = get_input("Enter your registered email: ")
            success, data = ProfileManager.view_profile(email)
            if success:
                print("\n👤 Your Profile:")
                for k, v in data.items():
                    print(f"   {k}: {v}")
            else:
                print(f"❌ {data}")

        elif choice == "5":
            print("👋 Exiting HabitHive. Stay productive!")
            break

        else:
            print("⚠️ Invalid choice. Try again.")


if __name__ == "__main__":
    init_firebase()  # Only run Firebase setup when executing the script
    main()
