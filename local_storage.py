import json
import os
from datetime import datetime
from typing import Dict, List, Any

class LocalGoalStorage:
    """Simple local file storage for goals when Firestore is unavailable"""
    
    def __init__(self, storage_file: str = 'local_goals.json'):
        self.storage_file = storage_file
        self.goals = self._load_goals()
    
    def _load_goals(self) -> Dict[str, List[Dict]]:
        """Load goals from local JSON file"""
        if os.path.exists(self.storage_file):
            try:
                with open(self.storage_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                print(f"Error loading goals: {e}")
                return {}
        return {}
    
    def _save_goals(self):
        """Save goals to local JSON file"""
        try:
            with open(self.storage_file, 'w', encoding='utf-8') as f:
                json.dump(self.goals, f, indent=2, default=str)
        except IOError as e:
            print(f"Error saving goals: {e}")
    
    def add_goal(self, user_id: str, goal_data: Dict[str, Any]) -> str:
        """Add a new goal for a user"""
        if user_id not in self.goals:
            self.goals[user_id] = []
        
        # Generate a simple ID
        goal_id = f"goal_{int(datetime.now().timestamp())}"
        goal_data['id'] = goal_id
        goal_data['createdAt'] = datetime.now().isoformat()
        
        self.goals[user_id].append(goal_data)
        self._save_goals()
        
        return goal_id
    
    def get_goals(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all goals for a user"""
        return self.goals.get(user_id, [])
    
    def update_goal(self, user_id: str, goal_id: str, update_data: Dict[str, Any]) -> bool:
        """Update an existing goal"""
        if user_id not in self.goals:
            return False
        
        for goal in self.goals[user_id]:
            if goal.get('id') == goal_id:
                goal.update(update_data)
                goal['updatedAt'] = datetime.now().isoformat()
                self._save_goals()
                return True
        
        return False
    
    def delete_goal(self, user_id: str, goal_id: str) -> bool:
        """Delete a goal"""
        if user_id not in self.goals:
            return False
        
        self.goals[user_id] = [
            goal for goal in self.goals[user_id] 
            if goal.get('id') != goal_id
        ]
        self._save_goals()
        return True

# Global instance
local_storage = LocalGoalStorage()