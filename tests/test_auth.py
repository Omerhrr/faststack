"""
Tests for FastStack Authentication

Tests user registration, login, password hashing, and session management.
"""

import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta


class TestPasswordHashing:
    """Tests for password hashing functionality."""

    def test_hash_password(self):
        """Test password hashing."""
        from faststack.auth.utils import hash_password
        
        password = "TestPassword123"
        hashed = hash_password(password)
        
        assert hashed != password
        assert hashed.startswith("$2b$")  # bcrypt prefix

    def test_verify_password_correct(self):
        """Test password verification with correct password."""
        from faststack.auth.utils import hash_password, verify_password
        
        password = "TestPassword123"
        hashed = hash_password(password)
        
        assert verify_password(password, hashed) is True

    def test_verify_password_incorrect(self):
        """Test password verification with incorrect password."""
        from faststack.auth.utils import hash_password, verify_password
        
        password = "TestPassword123"
        hashed = hash_password(password)
        
        assert verify_password("WrongPassword", hashed) is False

    def test_different_passwords_different_hashes(self):
        """Test that different passwords produce different hashes."""
        from faststack.auth.utils import hash_password
        
        hash1 = hash_password("password1")
        hash2 = hash_password("password2")
        
        assert hash1 != hash2

    def test_same_password_different_hashes(self):
        """Test that same password produces different hashes (bcrypt salt)."""
        from faststack.auth.utils import hash_password
        
        hash1 = hash_password("samepassword")
        hash2 = hash_password("samepassword")
        
        # bcrypt generates unique salts
        assert hash1 != hash2


class TestPasswordValidation:
    """Tests for password strength validation."""

    def test_validate_password_min_length(self):
        """Test minimum length validation."""
        from faststack.auth.utils import validate_password_strength
        from faststack.config import Settings
        
        settings = Settings(PASSWORD_MIN_LENGTH=8)
        
        with patch('faststack.auth.utils.settings', settings):
            is_valid, errors = validate_password_strength("short")
            
            assert is_valid is False
            assert any("at least" in e for e in errors)

    def test_validate_password_require_uppercase(self):
        """Test uppercase requirement."""
        from faststack.auth.utils import validate_password_strength
        from faststack.config import Settings
        
        settings = Settings(
            PASSWORD_MIN_LENGTH=4,
            PASSWORD_REQUIRE_UPPERCASE=True
        )
        
        with patch('faststack.auth.utils.settings', settings):
            is_valid, errors = validate_password_strength("lowercase123")
            
            assert is_valid is False
            assert any("uppercase" in e.lower() for e in errors)

    def test_validate_password_require_lowercase(self):
        """Test lowercase requirement."""
        from faststack.auth.utils import validate_password_strength
        from faststack.config import Settings
        
        settings = Settings(
            PASSWORD_MIN_LENGTH=4,
            PASSWORD_REQUIRE_LOWERCASE=True
        )
        
        with patch('faststack.auth.utils.settings', settings):
            is_valid, errors = validate_password_strength("UPPERCASE123")
            
            assert is_valid is False
            assert any("lowercase" in e.lower() for e in errors)

    def test_validate_password_require_digits(self):
        """Test digit requirement."""
        from faststack.auth.utils import validate_password_strength
        from faststack.config import Settings
        
        settings = Settings(
            PASSWORD_MIN_LENGTH=4,
            PASSWORD_REQUIRE_DIGITS=True
        )
        
        with patch('faststack.auth.utils.settings', settings):
            is_valid, errors = validate_password_strength("NoDigitsHere")
            
            assert is_valid is False
            assert any("digit" in e.lower() for e in errors)

    def test_validate_password_require_special(self):
        """Test special character requirement."""
        from faststack.auth.utils import validate_password_strength
        from faststack.config import Settings
        
        settings = Settings(
            PASSWORD_MIN_LENGTH=4,
            PASSWORD_REQUIRE_SPECIAL=True
        )
        
        with patch('faststack.auth.utils.settings', settings):
            is_valid, errors = validate_password_strength("NoSpecial123")
            
            assert is_valid is False
            assert any("special" in e.lower() for e in errors)

    def test_validate_password_strong(self):
        """Test validation passes for strong password."""
        from faststack.auth.utils import validate_password_strength
        from faststack.config import Settings
        
        settings = Settings(
            PASSWORD_MIN_LENGTH=8,
            PASSWORD_REQUIRE_UPPERCASE=True,
            PASSWORD_REQUIRE_LOWERCASE=True,
            PASSWORD_REQUIRE_DIGITS=True,
            PASSWORD_REQUIRE_SPECIAL=True
        )
        
        with patch('faststack.auth.utils.settings', settings):
            is_valid, errors = validate_password_strength("StrongP@ss123")
            
            assert is_valid is True
            assert errors == []


class TestUserCreation:
    """Tests for user creation."""

    def test_create_user(self, db_session):
        """Test creating a user."""
        from faststack.auth.utils import create_user
        
        user = create_user(
            session=db_session,
            email="test@example.com",
            password="TestPassword123",
        )
        
        assert user.id is not None
        assert user.email == "test@example.com"
        assert user.password_hash != "TestPassword123"
        assert user.is_active is True
        assert user.is_admin is False

    def test_create_admin_user(self, db_session):
        """Test creating an admin user."""
        from faststack.auth.utils import create_user
        
        user = create_user(
            session=db_session,
            email="admin@example.com",
            password="AdminPassword123",
            is_admin=True,
        )
        
        assert user.is_admin is True

    def test_create_user_with_extra_fields(self, db_session):
        """Test creating user with extra fields."""
        from faststack.auth.utils import create_user
        
        user = create_user(
            session=db_session,
            email="test@example.com",
            password="TestPassword123",
            first_name="Test",
            last_name="User",
        )
        
        assert user.first_name == "Test"
        assert user.last_name == "User"

    def test_create_duplicate_user_fails(self, db_session):
        """Test that creating duplicate users fails."""
        from faststack.auth.utils import create_user
        from sqlmodel.exc import IntegrityError
        
        create_user(
            session=db_session,
            email="test@example.com",
            password="TestPassword123",
        )
        
        with pytest.raises(IntegrityError):
            create_user(
                session=db_session,
                email="test@example.com",
                password="AnotherPassword",
            )


class TestUserAuthentication:
    """Tests for user authentication."""

    def test_authenticate_user_success(self, db_session, create_test_user):
        """Test successful authentication."""
        from faststack.auth.utils import authenticate_user
        
        user = create_test_user(email="test@example.com", password="TestPassword123")
        
        authenticated = authenticate_user(
            session=db_session,
            email="test@example.com",
            password="TestPassword123",
        )
        
        assert authenticated is not None
        assert authenticated.id == user.id

    def test_authenticate_user_wrong_password(self, db_session, create_test_user):
        """Test authentication with wrong password."""
        from faststack.auth.utils import authenticate_user
        
        create_test_user(email="test@example.com", password="TestPassword123")
        
        authenticated = authenticate_user(
            session=db_session,
            email="test@example.com",
            password="WrongPassword",
        )
        
        assert authenticated is None

    def test_authenticate_user_nonexistent(self, db_session):
        """Test authentication with non-existent user."""
        from faststack.auth.utils import authenticate_user
        
        authenticated = authenticate_user(
            session=db_session,
            email="nonexistent@example.com",
            password="AnyPassword",
        )
        
        assert authenticated is None

    def test_authenticate_inactive_user(self, db_session, create_test_user):
        """Test authentication of inactive user."""
        from faststack.auth.utils import authenticate_user
        
        create_test_user(email="inactive@example.com", password="TestPassword123", is_active=False)
        
        authenticated = authenticate_user(
            session=db_session,
            email="inactive@example.com",
            password="TestPassword123",
        )
        
        assert authenticated is None

    def test_authenticate_updates_last_login(self, db_session, create_test_user):
        """Test that authentication updates last_login."""
        from faststack.auth.utils import authenticate_user
        from datetime import datetime
        
        user = create_test_user(email="test@example.com", password="TestPassword123")
        
        # Set last_login to None
        user.last_login = None
        db_session.add(user)
        db_session.commit()
        
        # Authenticate
        authenticate_user(
            session=db_session,
            email="test@example.com",
            password="TestPassword123",
        )
        
        # Refresh user
        db_session.refresh(user)
        
        assert user.last_login is not None


class TestUserModel:
    """Tests for User model."""

    def test_user_display_name_with_names(self, db_session, create_test_user):
        """Test display_name with first and last name."""
        user = create_test_user(
            first_name="John",
            last_name="Doe",
        )
        
        assert user.display_name == "John Doe"

    def test_user_display_name_only_first(self, db_session, create_test_user):
        """Test display_name with only first name."""
        user = create_test_user(
            first_name="John",
            last_name=None,
        )
        
        assert user.display_name == "John"

    def test_user_display_name_only_last(self, db_session, create_test_user):
        """Test display_name with only last name."""
        user = create_test_user(
            first_name=None,
            last_name="Doe",
        )
        
        assert user.display_name == "Doe"

    def test_user_display_name_email_fallback(self, db_session, create_test_user):
        """Test display_name falls back to email."""
        user = create_test_user(
            first_name=None,
            last_name=None,
            email="test@example.com",
        )
        
        assert user.display_name == "test@example.com"

    def test_user_has_perm_superuser(self, db_session, create_test_user):
        """Test has_perm for superuser."""
        user = create_test_user(is_superuser=True)
        
        assert user.has_perm("any.permission") is True

    def test_user_has_perm_admin(self, db_session, create_test_user):
        """Test has_perm for admin user."""
        user = create_test_user(is_admin=True)
        
        assert user.has_perm("any.permission") is True

    def test_user_has_perm_regular_user(self, db_session, create_test_user):
        """Test has_perm for regular user."""
        user = create_test_user(is_admin=False, is_superuser=False)
        
        # Regular user without explicit permissions returns False
        assert user.has_perm("any.permission") is False


class TestBruteForceProtection:
    """Tests for brute force protection."""

    def test_record_failed_attempt(self):
        """Test recording failed attempts."""
        from faststack.auth.utils import record_failed_attempt, get_failed_attempts, clear_failed_attempts
        from faststack.config import Settings
        
        settings = Settings(BRUTE_FORCE_ENABLED=True, BRUTE_FORCE_LOCKOUT_DURATION=900)
        
        with patch('faststack.auth.utils.settings', settings):
            clear_failed_attempts("test@example.com")
            
            record_failed_attempt("test@example.com")
            record_failed_attempt("test@example.com")
            
            attempts = get_failed_attempts("test@example.com")
            assert attempts == 2

    def test_account_lockout_after_max_attempts(self):
        """Test account lockout after max attempts."""
        from faststack.auth.utils import (
            record_failed_attempt,
            is_account_locked,
            clear_failed_attempts
        )
        from faststack.config import Settings
        
        settings = Settings(
            BRUTE_FORCE_ENABLED=True,
            BRUTE_FORCE_MAX_ATTEMPTS=3,
            BRUTE_FORCE_LOCKOUT_DURATION=900
        )
        
        with patch('faststack.auth.utils.settings', settings):
            clear_failed_attempts("lockout@example.com")
            
            record_failed_attempt("lockout@example.com")
            record_failed_attempt("lockout@example.com")
            record_failed_attempt("lockout@example.com")
            
            assert is_account_locked("lockout@example.com") is True

    def test_clear_failed_attempts(self):
        """Test clearing failed attempts."""
        from faststack.auth.utils import (
            record_failed_attempt,
            get_failed_attempts,
            clear_failed_attempts
        )
        from faststack.config import Settings
        
        settings = Settings(BRUTE_FORCE_ENABLED=True, BRUTE_FORCE_LOCKOUT_DURATION=900)
        
        with patch('faststack.auth.utils.settings', settings):
            record_failed_attempt("clear@example.com")
            clear_failed_attempts("clear@example.com")
            
            attempts = get_failed_attempts("clear@example.com")
            assert attempts == 0

    def test_progressive_delay(self):
        """Test progressive delay calculation."""
        from faststack.auth.utils import get_progressive_delay, clear_failed_attempts, record_failed_attempt
        from faststack.config import Settings
        
        settings = Settings(
            BRUTE_FORCE_ENABLED=True,
            BRUTE_FORCE_PROGRESSIVE_DELAY=True,
            BRUTE_FORCE_LOCKOUT_DURATION=900
        )
        
        with patch('faststack.auth.utils.settings', settings):
            clear_failed_attempts("delay@example.com")
            
            # First failed attempt - no delay
            record_failed_attempt("delay@example.com")
            delay1 = get_progressive_delay("delay@example.com")
            
            # More attempts - increasing delay
            record_failed_attempt("delay@example.com")
            delay2 = get_progressive_delay("delay@example.com")
            
            assert delay1 >= 0
            assert delay2 >= delay1


class TestSessionManagement:
    """Tests for session management."""

    def test_login_user(self):
        """Test user login sets session correctly."""
        from faststack.core.session import login_user
        
        request = MagicMock()
        request.session = {}
        
        login_user(request, user_id=1)
        
        assert request.session["user_id"] == 1
        assert request.session["authenticated"] is True

    def test_login_user_with_extra_data(self):
        """Test user login with extra session data."""
        from faststack.core.session import login_user
        
        request = MagicMock()
        request.session = {}
        
        login_user(request, user_id=1, email="test@example.com")
        
        assert request.session["email"] == "test@example.com"

    def test_logout_user(self):
        """Test user logout clears session."""
        from faststack.core.session import login_user, logout_user
        
        request = MagicMock()
        request.session = {}
        
        login_user(request, user_id=1)
        logout_user(request)
        
        assert "user_id" not in request.session
        assert "authenticated" not in request.session

    def test_is_authenticated(self):
        """Test is_authenticated check."""
        from faststack.core.session import login_user, is_authenticated
        
        request = MagicMock()
        request.session = {}
        
        assert is_authenticated(request) is False
        
        login_user(request, user_id=1)
        
        assert is_authenticated(request) is True

    def test_flash_messages(self):
        """Test flash message functionality."""
        from faststack.core.session import flash, get_flashes
        
        request = MagicMock()
        request.session = {}
        
        flash(request, "Success message", "success")
        flash(request, "Error message", "error")
        
        flashes = get_flashes(request)
        
        assert len(flashes) == 2
        assert flashes[0]["message"] == "Success message"
        assert flashes[0]["category"] == "success"

    def test_session_regeneration(self):
        """Test session regeneration for security."""
        from faststack.core.session import regenerate_session, get_session_id
        
        request = MagicMock()
        request.session = {"user_id": 1, "old_data": "preserved"}
        
        old_session_id = get_session_id(request)
        new_session_id = regenerate_session(request)
        
        assert new_session_id is not None
        assert old_session_id != new_session_id
        assert request.session["user_id"] == 1  # Data preserved
