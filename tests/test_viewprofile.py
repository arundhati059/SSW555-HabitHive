import pytest
from flask import Flask
from web_app import app  # import your Flask instance

@pytest.fixture
def client():
    with app.test_client() as client:
        yield client

def test_add_journal_entry_success(client, mocker):
    mocker.patch("app.db.collection")  # mock Firestore
    response = client.post("/journal", json={
        "user_id": "12345",
        "entry_text": "Today was a great day!"
    })
    assert response.status_code == 200
    assert response.json["message"] == "Journal entry added successfully"

def test_add_journal_entry_missing_user_id(client):
    response = client.post("/journal", json={
        "entry_text": "Missing user id"
    })
    assert response.status_code == 400
    assert "error" in response.json

def test_add_journal_entry_missing_text(client):
    response = client.post("/journal", json={
        "user_id": "12345"
    })
    assert response.status_code == 400
    assert "error" in response.json
