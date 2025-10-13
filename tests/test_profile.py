def test_profile_creation():
    profile = {"display_name": "Yasaswini", "avatar": "avatar1.png"}
    assert profile["display_name"] == "Yasaswini"
    assert profile["avatar"].endswith(".png")
