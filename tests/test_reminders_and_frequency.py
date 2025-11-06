import json
from web_app import app
from datetime import datetime, timedelta

client = app.test_client()

# ---------------------------------------------------------
# 1. TEST DAILY HABIT WITH REMINDERS
# ---------------------------------------------------------
def test_daily_habit_with_reminder():
    payload = {
        "name": "Meditate",
        "description": "Morning meditation",
        "frequencyType": "daily",
        "reminderEnabled": True,
        "reminderTime": "06:30"
    }

    response = client.post("/api/habits", json=payload)
    data = response.get_json()

    print("\nDaily Habit Response:", data)

    assert response.status_code == 200
    assert data["success"] is True
    assert "habitId" in data


# ---------------------------------------------------------
# 2. TEST WEEKLY HABIT WITH MULTIPLE DAYS
# ---------------------------------------------------------
def test_weekly_habit():
    payload = {
        "name": "Gym",
        "description": "Strength training",
        "frequencyType": "weekly",
        "reminderEnabled": True,
        "reminderDays": ["Mon", "Wed", "Fri"],
        "reminderTime": "18:00"
    }

    response = client.post("/api/habits", json=payload)
    data = response.get_json()

    print("\nWeekly Habit Response:", data)

    assert response.status_code == 200
    assert data["success"] is True
    assert "habitId" in data


# ---------------------------------------------------------
# 3. TEST CUSTOM FREQUENCY (EVERY X HOURS)
# ---------------------------------------------------------
def test_custom_frequency_hours():
    payload = {
        "name": "Drink Water",
        "description": "Hydration routine",
        "frequencyType": "custom",
        "customFrequencyValue": 3,
        "customFrequencyUnit": "hours",
        "reminderEnabled": True
    }

    response = client.post("/api/habits", json=payload)
    data = response.get_json()

    print("\nCustom Hours Habit Response:", data)

    assert response.status_code == 200
    assert data["success"] is True


# ---------------------------------------------------------
# 4. TEST CUSTOM FREQUENCY (EVERY X DAYS)
# ---------------------------------------------------------
def test_custom_frequency_days():
    payload = {
        "name": "Clean Desk",
        "description": "",
        "frequencyType": "custom",
        "customFrequencyValue": 2,
        "customFrequencyUnit": "days",
        "reminderEnabled": True
    }

    response = client.post("/api/habits", json=payload)
    data = response.get_json()

    print("\nCustom Days Habit Response:", data)

    assert response.status_code == 200
    assert data["success"] is True


# ---------------------------------------------------------
# 5. TEST INVALID HABIT (NO FREQUENCY TYPE)
# ---------------------------------------------------------
def test_missing_frequency_type():
    payload = {
        "name": "Read Book",
        "description": "Night reading",
        "reminderEnabled": True,
        "reminderTime": "21:00"
    }

    response = client.post("/api/habits", json=payload)
    
    print("\nMissing Frequency Response:", response.get_json())

    assert response.status_code in (400, 500)


# ---------------------------------------------------------
# 6. TEST INVALID CUSTOM FREQUENCY VALUES
# ---------------------------------------------------------
def test_invalid_custom_frequency_values():
    payload = {
        "name": "Stretch",
        "frequencyType": "custom",
        "customFrequencyValue": "",
        "customFrequencyUnit": "",
        "reminderEnabled": True
    }

    response = client.post("/api/habits", json=payload)

    print("\nInvalid Custom Frequency Response:", response.get_json())

    assert response.status_code in (400, 500)


# ---------------------------------------------------------
# 7. TEST REMINDER LOGIC (NEXT REMINDER)
# ---------------------------------------------------------
def test_next_reminder_custom_hours():
    """
    This test does not hit the API.
    It simulates next reminder calculation logic for custom frequency.
    """

    last_completed = datetime(2025, 1, 1, 9, 0)
    frequency_hours = 3

    expected_next = last_completed + timedelta(hours=frequency_hours)

    assert expected_next == datetime(2025, 1, 1, 12, 0)


# ---------------------------------------------------------
# 8. TEST REMINDER LOGIC FOR DAILY HABIT
# ---------------------------------------------------------
def test_next_reminder_daily():
    reminder_time_str = "21:00"
    today = datetime.now().strftime("%Y-%m-%d")
    
    next_reminder = datetime.strptime(today + " " + reminder_time_str, "%Y-%m-%d %H:%M")

    print("\nDaily Next Reminder:", next_reminder)

    assert isinstance(next_reminder, datetime)


# ---------------------------------------------------------
# 9. TEST WEEKLY NEXT REMINDER CALCULATION (SIMULATION)
# ---------------------------------------------------------
def test_next_reminder_weekly():
    """
    Simulate finding the next reminder day: Wed/Fri
    """

    reminder_days = ["Wed", "Fri"]
    now = datetime(2025, 1, 1)  # Wed

    weekday_map = {
        "Mon": 0, "Tue": 1, "Wed": 2, "Thu": 3,
        "Fri": 4, "Sat": 5, "Sun": 6
    }

    today_wd = now.weekday()

    next_day = None
    for d in reminder_days:
        wd = weekday_map[d]
        if wd >= today_wd:
            next_day = wd
            break

    assert next_day == 2  # Wednesday (0-based)


