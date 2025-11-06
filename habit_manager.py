import json
from datetime import date, timedelta
from pathlib import Path

DATA_FILE = Path.home() / ".habit_data.json"

class HabitManager:
    """Handles habit creation, tracking, and review."""

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
        """Step 1: Define habit clearly"""
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

    def create_habit(self, name, purpose, frequency, timing, reminder=None):
        """Create a new habit programmatically."""
        if name in self.data["habits"]:
            raise ValueError(f"Habit '{name}' already exists.")

        self.data["habits"][name] = {
            "purpose": purpose,
            "frequency": frequency,
            "timing": timing,
            "reminder": reminder or "",
            "progress": {}
        }
        self.save_data()
        return f"Habit '{name}' created successfully!"

    def mark_done(self):
        """Step 5: Track progress daily"""
        name = input("Enter habit name to mark as done: ").strip()
        if name not in self.data["habits"]:
            print("❌ Habit not found.")
            return

        today = str(date.today())
        self.data["habits"][name]["progress"][today] = True
        self.save_data()
        print(f"✅ '{name}' marked as done for today!")

    def view_progress(self):
        """Show progress summary"""
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
        """Step 6: Review and adjust regularly"""
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

    def create_journal_entry(self, title, content):
        """Create a new journal entry."""
        journal_file = Path.home() / ".journal_entries.json"

        # Load existing journal entries
        if journal_file.exists():
            with open(journal_file, "r") as f:
                journal_data = json.load(f)
        else:
            journal_data = {"entries": []}

        # Add the new entry
        entry = {
            "title": title,
            "content": content,
            "date": str(date.today())
        }
        journal_data["entries"].append(entry)

        # Save the updated journal entries
        with open(journal_file, "w") as f:
            json.dump(journal_data, f, indent=2)

        return f"Journal entry '{title}' created successfully!"

    def show_menu(self):
        """Main habit menu — runs after login"""
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
    manager = HabitManager()
    manager.show_menu()



