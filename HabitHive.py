
import os
import re
import firebase_admin
from firebase_admin import credentials, auth
from dotenv import load_dotenv
import json
from datetime import date, timedelta
from pathlib import Path

DATA_FILE = Path.home() / ".habit_data.json"

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
            # Note: Firebase Admin SDK doesn't support direct email/password sign-in
            # In a real app, you'd use Firebase Client SDK or verify through a custom token
            # This is a simplified version that just checks if the user exists
            user = auth.get_user_by_email(email)
            return True, f"Login successful! Welcome, {user.email}"
        except auth.UserNotFoundError:
            return False, "Invalid email or password"
        except Exception as e:
            return False, f"Login error: {str(e)}"

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
                print("Redirecting to Habit Manager...\n")
                habit_manager = HabitManager()
                habit_manager.show_menu()
                break
        
        elif choice == "3":
            print("Thank you for using HabitHive!")
            break
        
        else:
            print("Invalid choice. Please try again.")
class HabitManager:

    def __init__(self):
        self.data = self.load_data()

    def load_data(self):
        if not DATA_FILE.exists():
            return {"habits": {}}
        with open(DATA_FILE, "r") as f:
            return json.load(f)

    def save_data(self):
        with open(DATA_FILE, "w") as f:
            json.dump(self.data, f, indent=2)

    def define_habit(self):
        name = input("Enter a habit name: ").strip()
        if name in self.data["habits"]:
            print("⚠️ Habit already exists.")
            return

        purpose = input("Enter the purpose of this habit: ").strip()
        frequency = input("Enter frequency (e.g., daily, 3/week): ").strip()
        timing = input("Enter preferred time (e.g., 07:30 AM or evening): ").strip()
        reminder = input("Set a reminder note (optional): ").strip()

        self.data["habits"][name] = {
            "purpose": purpose,
            "frequency": frequency,
            "timing": timing,
            "reminder": reminder,
            "progress": {}
        }

        self.save_data()
        print(f"✅ Habit '{name}' created successfully!")

    def mark_done(self):
        name = input("Enter habit name to mark as done: ").strip()
        if name not in self.data["habits"]:
            print("❌ Habit not found.")
            return

        today = str(date.today())
        self.data["habits"][name]["progress"][today] = True
        self.save_data()
        print(f"✅ '{name}' marked as done for today!")

    def view_progress(self):
        if not self.data["habits"]:
            print("No habits yet. Add one first.")
            return

        for name, info in self.data["habits"].items():
            completed = len(info["progress"])
            print(f"\n📊 {name}")
            print(f"   Purpose: {info['purpose']}")
            print(f"   Frequency: {info['frequency']}")
            print(f"   Timing: {info['timing']}")
            print(f"   Reminder: {info['reminder']}")
            print(f"   Days completed: {completed}")

    def review_and_adjust(self):
        name = input("Enter habit name to review: ").strip()
        if name not in self.data["habits"]:
            print("❌ Habit not found.")
            return

        info = self.data["habits"][name]
        print(f"\nReviewing '{name}':")
        print(f"Purpose: {info['purpose']}")
        print(f"Frequency: {info['frequency']}")
        print(f"Timing: {info['timing']}")
        print(f"Reminder: {info['reminder']}")
        print(f"Completed days: {len(info['progress'])}")

        adjust = input("Would you like to edit this habit? (y/n): ").strip().lower()
        if adjust == "y":
            info["purpose"] = input("New purpose (leave blank to keep): ") or info["purpose"]
            info["frequency"] = input("New frequency (leave blank to keep): ") or info["frequency"]
            info["timing"] = input("New timing (leave blank to keep): ") or info["timing"]
            info["reminder"] = input("New reminder (leave blank to keep): ") or info["reminder"]
            self.save_data()
            print("✅ Habit updated successfully!")

    def show_menu(self):
        while True:
            print("\n🌱 Habit Manager")
            print("1. Define a new habit")
            print("2. Mark habit as done")
            print("3. View progress")
            print("4. Review and adjust")
            print("5. Exit to main menu")

            choice = input("Choose an option (1–5): ").strip()
            if choice == "1":
                self.define_habit()
            elif choice == "2":
                self.mark_done()
            elif choice == "3":
                self.view_progress()
            elif choice == "4":
                self.review_and_adjust()
            elif choice == "5":
                print("Returning to main menu...")
                break
            else:
                print("Invalid choice, try again.")            

if __name__ == "__main__":
    init_firebase()  # Only run Firebase setup when executing the script
    main()
