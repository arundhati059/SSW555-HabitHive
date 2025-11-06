import json
from app import app

def test_create_custom_frequency_habit():
    client = app.test_client()

    payload = {
        "name": "Drink water",
        "description": "Stay hydrated",
        "frequencyType": "custom",
        "customFrequencyValue": 3,
        "customFrequencyUnit": "hours",
        "reminderEnabled": True
    }

    response = client.post("/api/habits", json=payload)
    
    assert response.status_code == 200
    data = response.get_json()

    assert data["success"] == True
    assert "habitId" in data


def test_invalid_custom_frequency():
    client = app.test_client()

    payload = {
        "name": "Stretch",
        "frequencyType": "custom",
        "customFrequencyValue": "",
        "customFrequencyUnit": "",
        "reminderEnabled": True
    }

    response = client.post("/api/habits", json=payload)
    
    assert response.status_code == 400 or response.status_code == 500
