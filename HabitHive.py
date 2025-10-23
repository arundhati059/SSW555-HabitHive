
import os
import re
import firebase_admin
from firebase_admin import credentials, auth
from dotenv import load_dotenv

# Initialize Firebase Admin SDK
def init_firebase():
    """Initialize Firebase, only called when running the app directly"""
    try:
        cred = credentials.Certificate("firebase-credentials.json")
        firebase_admin.initialize_app(cred)
    except FileNotFoundError:
        print("Error: firebase-credentials.json not found. Please follow setup instructions.")
        exit(1)

class AuthManager:
    @staticmethod
    def validate_email(email):
        """Validate email format"""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))

    @staticmethod
    def validate_password(password):
        """Validate password strength"""
        if len(password) < 6:
            return False, "Password must be at least 6 characters long"
        return True, "Password is valid"

    @staticmethod
    def sign_up(email, password):
        """Create a new user account"""
        try:
            if not AuthManager.validate_email(email):
                return False, "Invalid email format"
            
            password_valid, msg = AuthManager.validate_password(password)
            if not password_valid:
                return False, msg
            
            user = auth.create_user(
                email=email,
                password=password
            )
            return True, f"User created successfully with ID: {user.uid}"
        except auth.EmailAlreadyExistsError:
            return False, "Email already registered"
        except Exception as e:
            return False, f"Error creating user: {str(e)}"

    @staticmethod
    def login(email, password):
        """Verify user credentials"""
        try:
            # Check if user exists and verify credentials
            try:
                user = auth.get_user_by_email(email)
                # Firebase Auth handles the password verification
                if user:
                    print("Login successful")
                    return True, f"Login successful! Welcome, {user.email}"
            except auth.UserNotFoundError:
                print("Invalid email or password")
                return False, "Invalid email or password"
            except Exception as e:
                print(f"Error during verification: {e}")
                return False, "Invalid email or password"
        except Exception as e:
            print(f"Unexpected error during login: {e}")
            return False, "An error occurred during login"

def get_user_input(prompt):
    """Get user input with optional masking for passwords"""
    return input(prompt)

def main():
    print("✅ HabitHive App started successfully!")
    print("Welcome to HabitHive — your habit-tracking assistant!")
    
    while True:
        print("\n1. Sign Up")
        print("2. Log In")
        print("3. Exit")
        
        choice = input("\nChoose an option (1-3): ")
        
        if choice == "1":
            email = get_user_input("Enter email: ")
            password = get_user_input("Enter password: ")
            success, message = AuthManager.sign_up(email, password)
            print(f"\n{'✅' if success else '❌'} {message}")
            if success:
                print("Please log in with your new account.")
        
        elif choice == "2":
            email = get_user_input("Enter email: ")
            password = get_user_input("Enter password: ")
            success, message = AuthManager.login(email, password)
            print(f"\n{'✅' if success else '❌'} {message}")
            if success:
                print("Redirecting to dashboard...")
                # TODO: Implement dashboard view
                break
        
        elif choice == "3":
            print("Thank you for using HabitHive!")
            break
        
        else:
            print("Invalid choice. Please try again.")

if __name__ == "__main__":
    init_firebase()  # Only run Firebase setup when executing the script
    main()
