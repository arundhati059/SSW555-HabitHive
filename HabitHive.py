
import os
import re
import firebase_admin
from firebase_admin import credentials, auth
from dotenv import load_dotenv
import requests


API_KEY = "AIzaSyDZ67THtlAFUJIi5hi1-9n16-hCHnCR2Ec" #Must be removed before deployment
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
