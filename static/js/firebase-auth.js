// Firebase Frontend Configuration and Authentication
// Import Firebase functions
import { 
    createUserWithEmailAndPassword, 
    signInWithEmailAndPassword, 
    signOut,
    onAuthStateChanged 
} from 'https://www.gstatic.com/firebasejs/10.7.0/firebase-auth.js';

// Firebase Authentication functions
class FirebaseAuthManager {
    constructor() {
        this.auth = window.firebaseAuth;
        this.setupAuthStateListener();
    }

    // Sign up new user
    async signUp(email, password) {
        try {
            const userCredential = await createUserWithEmailAndPassword(this.auth, email, password);
            return { success: true, user: userCredential.user };
        } catch (error) {
            console.error('Firebase signup error:', error);
            return { 
                success: false, 
                error: this.getErrorMessage(error.code) || 'An unknown error occurred during signup.'
            };
        }
    }

    // Sign in existing user
    async signIn(email, password) {
        try {
            const userCredential = await signInWithEmailAndPassword(this.auth, email, password);
            return { success: true, user: userCredential.user };
        } catch (error) {
            return { success: false, error: this.getErrorMessage(error.code) };
        }
    }

    // Sign out user
    async signOut() {
        try {
            await signOut(this.auth);
            return { success: true };
        } catch (error) {
            return { success: false, error: error.message };
        }
    }

    // Set up auth state listener
    setupAuthStateListener() {
        onAuthStateChanged(this.auth, (user) => {
            if (user) {
                this.handleAuthenticatedUser(user);
            } else {
                this.handleUnauthenticatedUser();
            }
        });
    }

    // Handle authenticated user
    async handleAuthenticatedUser(user) {
        // Get ID token and send to backend
        try {
            const idToken = await user.getIdToken();
            const response = await fetch('/verify-token', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ idToken: idToken })
            });

            if (response.ok) {
                const data = await response.json();
                if (data.success) {
                    // Redirect to dashboard if on login/signup page
                    if (window.location.pathname === '/login' || window.location.pathname === '/signup') {
                        window.location.href = '/dashboard';
                    }
                }
            }
        } catch (error) {
            console.error('Auth verification error:', error);
        }
    }

    // Handle unauthenticated user
    handleUnauthenticatedUser() {
        // Don't redirect if user is on logout page (let it complete)
        if (window.location.pathname === '/logout') {
            return;
        }
        
        // Redirect to login if on protected page
        if (window.location.pathname === '/dashboard') {
            window.location.href = '/login';
        }
    }

    // Get user-friendly error messages
    getErrorMessage(errorCode) {
        switch (errorCode) {
            case 'auth/user-not-found':
                return 'No user found with this email.';
            case 'auth/wrong-password':
                return 'Incorrect password. Please try again.';
            case 'auth/email-already-in-use':
                return 'This email is already in use.';
            case 'auth/weak-password':
                return 'Password is too weak. Please choose a stronger password.';
            case 'auth/invalid-email':
                return 'Please enter a valid email address.';
            case 'auth/too-many-requests':
                return 'Too many failed attempts. Please try again later.';
            case 'auth/network-request-failed':
                return 'Network error. Please check your connection.';
            case 'auth/invalid-credential':
                return 'Invalid email or password.';
            case 'auth/operation-not-allowed':
                return 'Email/password accounts are not enabled.';
            case 'auth/user-disabled':
                return 'This account has been disabled.';
            case 'auth/requires-recent-login':
                return 'Please log out and log back in to continue.';
            default:
                return `Error: ${errorCode}. Please try again.`;
        }
    }

    // Validate email format
    isValidEmail(email) {
        const emailPattern = /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/;
        return emailPattern.test(email);
    }

    // Validate password strength
    isValidPassword(password) {
        return password.length >= 6;
    }
}

// Initialize Firebase Auth Manager when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    window.authManager = new FirebaseAuthManager();
});

// Export for use in other scripts
window.FirebaseAuthManager = FirebaseAuthManager;