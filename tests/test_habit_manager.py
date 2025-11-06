import unittest
from unittest.mock import patch, MagicMock
import sys
import os
import firebase_admin
from firebase_admin import auth, credentials

# Setup Firebase mocking
@patch('firebase_admin.credentials.Certificate')
@patch('firebase_admin.initialize_app')
def setup_firebase_mocks(mock_init, mock_cert):
    mock_cert.return_value = MagicMock()
    mock_init.return_value = MagicMock()
    return mock_init, mock_cert

# Initialize mocks before tests
mock_init, mock_cert = setup_firebase_mocks()

# Ensure Firebase app is initialized for tests
firebase_admin._apps = {None: MagicMock()}

# Add the project root directory to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from HabitHive import AuthManager

class TestAuthentication(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """Set up test fixtures before all test methods."""
        # Ensure Firebase app is initialized
        if not firebase_admin._apps:
            cred = credentials.Certificate("tests/dummy-credentials.json")
            firebase_admin.initialize_app(cred)
    
    def setUp(self):
        """Set up test fixtures before each test method."""
        self.auth_manager = AuthManager

    def test_email_validation(self):
        """Test email validation according to acceptance criteria"""
        # Valid email cases
        self.assertTrue(self.auth_manager.validate_email("test@example.com"))
        self.assertTrue(self.auth_manager.validate_email("user.name@domain.co.uk"))
        
        # Invalid email cases
        self.assertFalse(self.auth_manager.validate_email("invalid-email"))
        self.assertFalse(self.auth_manager.validate_email("@domain.com"))
        self.assertFalse(self.auth_manager.validate_email("user@.com"))

    def test_password_validation(self):
        """Test password validation according to acceptance criteria"""
        # Valid password case
        is_valid, message = self.auth_manager.validate_password("password123")
        self.assertTrue(is_valid)
        
        # Invalid password cases (too short)
        is_valid, message = self.auth_manager.validate_password("12345")
        self.assertFalse(is_valid)
        self.assertEqual(message, "Password must be at least 6 characters long")

    @patch('HabitHive.auth.create_user')
    def test_successful_signup(self, mock_create_user):
        """Test successful user signup"""
        # Mock the Firebase auth response
        test_uid = "test123"
        mock_user = MagicMock()
        mock_user.uid = test_uid
        mock_create_user.return_value = mock_user

        success, message = self.auth_manager.sign_up("test@example.com", "password123")
        
        # Verify success
        self.assertTrue(success)
        self.assertIn("User created successfully", message)
        self.assertIn(test_uid, message)
        
        # Verify Firebase was called correctly
        mock_create_user.assert_called_once_with(
            email="test@example.com",
            password="password123"
        )
    @patch('HabitHive.auth.create_user')
    def test_signup_with_existing_email(self, mock_create_user):
        """Test signup with already registered email"""
        # Mock Firebase throwing EmailAlreadyExistsError
        error_response = MagicMock()
        error_response.status_code = 400
        mock_create_user.side_effect = auth.EmailAlreadyExistsError('error', 'Email already exists', http_response=error_response)
        
        success, message = self.auth_manager.sign_up("existing@example.com", "password123")
        
        self.assertFalse(success)
        self.assertEqual(message, "Email already registered")

    @patch('firebase_admin.auth')
    def test_successful_login(self, mock_auth):
        """Test successful user login"""
        # Mock successful user lookup
        mock_user = MagicMock()
        mock_user.email = "test@example.com"
        mock_auth.get_user_by_email = MagicMock(return_value=mock_user)

        success, message = self.auth_manager.login("test@example.com", "password123")
        
        self.assertTrue(success)
        self.assertIn("Login successful", message)
        self.assertIn("test@example.com", message)

    @patch('firebase_admin.auth')
    def test_login_with_invalid_credentials(self, mock_auth):
        """Test login with invalid credentials"""
        # Mock Firebase throwing UserNotFoundError
        mock_auth.get_user_by_email.side_effect = auth.UserNotFoundError('error', 'User not found')
        
        success, message = self.auth_manager.login("nonexistent@example.com", "password123")
        
        self.assertFalse(success)
        self.assertEqual(message, "Invalid email or password")

if __name__ == '__main__':
    unittest.main()
