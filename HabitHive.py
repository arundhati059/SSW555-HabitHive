import os
import re
import json
from datetime import datetime
from getpass import getpass
import requests  # Add this import at the top

# ... (keep all your existing code for DATA_FILE, AVATAR_DIR, helper functions)

# Load Firebase credentials
with open('firebase-credentials.json', 'r') as f:
    firebase_config = json.load(f)

class AuthManager:
    """Handles Firebase Authentication via REST API."""
    
    # Get API key from credentials file
    API_KEY = firebase_config.get('API_KEY')
    
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
        """Sign up new user using Firebase REST API"""
        if not AuthManager.validate_email(email):
            return False, "Invalid email format"
        
        password_valid, msg = AuthManager.validate_password(password)
        if not password_valid:
            return False, msg
        
        url = f"https://identitytoolkit.googleapis.com/v1/accounts:signUp?key={AuthManager.API_KEY}"
        
        payload = {
            "email": email,
            "password": password,
            "returnSecureToken": True
        }
        
        try:
            response = requests.post(url, json=payload)
            result = response.json()
            
            if 'error' in result:
                error_message = result['error']['message']
                if error_message == "EMAIL_EXISTS":
                    return False, "Email already registered."
                return False, f"Sign up failed: {error_message}"
            
            if 'idToken' in result:
                # Create local profile entry
                users = load_users()
                new_user = {
                    "email": email,
                    "firebase_uid": result.get('localId'),
                    "created_at": str(datetime.now()),
                    "profile": None
                }
                users.append(new_user)
                save_users(users)
                
                return True, f"User created successfully with email: {email}"
            
            return False, "Unknown error occurred"
            
        except Exception as e:
            return False, f"Sign up error: {str(e)}"
    
    @staticmethod
    def login(email, password):
        """Login user using Firebase REST API"""
        url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={AuthManager.API_KEY}"
        
        payload = {
            "email": email,
            "password": password,
            "returnSecureToken": True
        }
        
        try:
            response = requests.post(url, json=payload)
            result = response.json()
            
            if 'error' in result:
                error_message = result['error']['message']
                if error_message == "EMAIL_NOT_FOUND":
                    return False, "User not found."
                elif error_message == "INVALID_PASSWORD":
                    return False, "Incorrect password."
                elif error_message == "INVALID_LOGIN_CREDENTIALS":
                    return False, "Invalid email or password."
                return False, f"Login failed: {error_message}"
            
            if 'idToken' in result:
                return True, f"Welcome back, {email}!"
            
            return False, "Unknown error occurred"
            
        except Exception as e:
            return False, f"Login error: {str(e)}"

# Keep the rest of your ProfileManager class unchanged
