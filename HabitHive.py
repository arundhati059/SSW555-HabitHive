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
        """Create a new user account using Firebase REST API"""
        try:
            if not AuthManager.validate_email(email):
                return False, "Invalid email format"
            
            password_valid, msg = AuthManager.validate_password(password)
            if not password_valid:
                return False, msg
            
            # Use Firebase REST API for signup
            url = f"https://identitytoolkit.googleapis.com/v1/accounts:signUp?key={API_KEY}"
            payload = {
                "email": email,
                "password": password,
                "returnSecureToken": True
            }
            
            response = requests.post(url, json=payload)
            
            print(f"Signup response status: {response.status_code}")
            print(f"Signup response body: {response.text}")
            
            if response.status_code == 200:
                response_data = response.json()
                print(f"Signup successful for: {response_data.get('email')}")
                return True, f"Account created successfully!"
            else:
                try:
                    error_data = response.json()
                    error_message = error_data.get('error', {}).get('message', 'Signup failed')
                    
                    # Handle common Firebase auth errors
                    if 'EMAIL_EXISTS' in error_message:
                        return False, "Email already registered. Please try logging in instead."
                    elif 'WEAK_PASSWORD' in error_message:
                        return False, "Password is too weak. Please choose a stronger password."
                    elif 'INVALID_EMAIL' in error_message:
                        return False, "Invalid email format."
                    else:
                        return False, f"Signup failed: {error_message}"
                except:
                    return False, f"Signup failed with status {response.status_code}"
                    
        except requests.exceptions.RequestException as e:
            print(f"Network error during signup: {e}")
            return False, "Network error. Please check your connection and try again."
        except Exception as e:
            print(f"Unexpected error during signup: {e}")
            return False, "An unexpected error occurred during signup."

    @staticmethod
    def login(email, password):
        """Verify user credentials using Firebase REST API"""
        try:
            # Use Firebase REST API for authentication
            url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={API_KEY}"
            payload = {
                "email": email,
                "password": password,
                "returnSecureToken": True
            }
            
            response = requests.post(url, json=payload)
            
            if response.status_code == 200:
                response_data = response.json()
                return True, f"Login successful! Welcome, {response_data.get('email')}"
            else:
                error_data = response.json()
                error_message = error_data.get('error', {}).get('message', 'Login failed')
                
                # Handle common Firebase auth errors
                if 'INVALID_PASSWORD' in error_message:
                    return False, "Invalid email or password"
                elif 'EMAIL_NOT_FOUND' in error_message:
                    return False, "Invalid email or password"
                elif 'USER_DISABLED' in error_message:
                    return False, "This account has been disabled"
                elif 'TOO_MANY_ATTEMPTS_TRY_LATER' in error_message:
                    return False, "Too many failed attempts. Please try again later"
                else:
                    return False, "Login failed. Please check your credentials"
                    
        except requests.exceptions.RequestException as e:
            print(f"Network error during login: {e}")
            return False, "Network error. Please check your connection and try again"
        except Exception as e:
            print(f"Unexpected error during login: {e}")
            return False, "An unexpected error occurred during login"

def get_user_input(prompt):
    """Get user input with optional masking for passwords"""
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
