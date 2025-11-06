# create_habit.py (or habit_manager.py - whatever you named it)
import os
import json
from datetime import datetime, timedelta


class HabitManager:
    """Simple habit management without user authentication."""
    
    HABITS_FILE = "habits.json"
    
    @staticmethod
    def create_habit(habit_name, description="", frequency="daily", target_count=1, category="General", privacy="public"):
        """
        Create a new habit.
        
        Args:
            habit_name: Name of the habit
            description: Optional description
            frequency: How often (daily, weekly, monthly)
            target_count: Target completions per frequency period
            category: Habit category
            privacy: Privacy setting (public, friends, private)
        
        Returns:
            (success: bool, message: str)
        """
        # Validate inputs
        if not habit_name.strip():
            return False, "Habit name cannot be empty."
        
        if frequency not in ["daily", "weekly", "monthly"]:
            return False, "Frequency must be daily, weekly, or monthly."
        
        if target_count < 1:
            return False, "Target count must be at least 1."
        
        if privacy not in ["public", "friends", "private"]:
            privacy = "public"  # Default to public if invalid
        
        # Create habit object
        new_habit = {
            "name": habit_name.strip(),
            "description": description.strip(),
            "frequency": frequency,
            "target_count": target_count,
            "category": category,
            "privacy": privacy,  # Add privacy field
            "created_at": str(datetime.now()),
            "is_active": True,
            "streak": 0,
            "total_completions": 0,
            "completion_history": []
        }
        
        # Load existing habits
        habits = HabitManager._load_habits()
        
        # Check if habit already exists
        if any(h["name"].lower() == habit_name.lower() for h in habits):
            return False, f"Habit '{habit_name}' already exists."
        
        # Add new habit
        habits.append(new_habit)
        HabitManager._save_habits(habits)
        
        return True, f"✅ Habit '{habit_name}' created successfully!"
    
    @staticmethod
    def get_all_habits(active_only=True):
        """
        Get all habits.
        
        Args:
            active_only: If True, only return active habits
        
        Returns:
            list of habits
        """
        habits = HabitManager._load_habits()
        
        if active_only:
            habits = [h for h in habits if h.get("is_active", True)]
        
        return habits
    
    @staticmethod
    def complete_habit(habit_name):
        """
        Mark a habit as completed for today.
        
        Args:
            habit_name: Name of the habit to complete
        
        Returns:
            (success: bool, message: str)
        """
        habits = HabitManager._load_habits()
        today = datetime.now().date().isoformat()
        
        for habit in habits:
            if habit["name"].lower() == habit_name.lower():
                # Check if already completed today
                if today in habit.get("completion_history", []):
                    return False, "Habit already completed today!"
                
                # Add completion
                if "completion_history" not in habit:
                    habit["completion_history"] = []
                habit["completion_history"].append(today)
                
                # Update stats
                habit["total_completions"] = habit.get("total_completions", 0) + 1
                habit["streak"] = HabitManager._calculate_streak(habit["completion_history"])
                
                HabitManager._save_habits(habits)
                return True, f"✅ '{habit_name}' completed! Current streak: {habit['streak']} days 🔥"
        
        return False, f"Habit '{habit_name}' not found."
    
    @staticmethod
    def delete_habit(habit_name):
        """
        Delete a habit.
        
        Args:
            habit_name: Name of the habit to delete
        
        Returns:
            (success: bool, message: str)
        """
        habits = HabitManager._load_habits()
        
        for habit in habits:
            if habit["name"].lower() == habit_name.lower():
                habit["is_active"] = False
                HabitManager._save_habits(habits)
                return True, f"Habit '{habit_name}' deleted successfully."
        
        return False, f"Habit '{habit_name}' not found."
    
    @staticmethod
    def _load_habits():
        """Load habits from JSON file."""
        if not os.path.exists(HabitManager.HABITS_FILE):
            return []
        with open(HabitManager.HABITS_FILE, "r") as f:
            return json.load(f)
    
    @staticmethod
    def _save_habits(habits):
        """Save habits to JSON file."""
        with open(HabitManager.HABITS_FILE, "w") as f:
            json.dump(habits, f, indent=4)
    
    @staticmethod
    def _calculate_streak(completion_history):
        """Calculate current streak from completion history."""
        if not completion_history:
            return 0
        
        sorted_dates = sorted([datetime.fromisoformat(d).date() for d in completion_history], reverse=True)
        
        streak = 0
        current_date = datetime.now().date()
        
        for completion_date in sorted_dates:
            if completion_date == current_date:
                streak += 1
                current_date -= timedelta(days=1)
            elif completion_date < current_date:
                break
