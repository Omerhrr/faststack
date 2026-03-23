"""
FastStack Password Validators

Django-like password validation for enforcing password policies.

Example:
    from faststack.auth.validators import (
        validate_password,
        UserAttributeSimilarityValidator,
        MinimumLengthValidator,
        CommonPasswordValidator,
        NumericPasswordValidator
    )

    # Validate password
    try:
        validate_password('MySecurePassword123!', user=user)
    except ValidationError as e:
        print(e.messages)
"""

from typing import Any, Dict, List, Optional, Type
from dataclasses import dataclass
from difflib import SequenceMatcher
import re


@dataclass
class ValidationError(Exception):
    """Validation error with messages."""
    messages: List[str]

    def __init__(self, messages: List[str] = None, code: str = None):
        self.messages = messages or []
        self.code = code


class BasePasswordValidator:
    """
    Base class for password validators.
    """

    def __init__(self, options: Dict[str, Any] = None):
        """Initialize validator with options."""
        self.options = options or {}

    def validate(self, password: str, user: Any = None) -> None:
        """
        Validate the password.

        Args:
            password: The password to validate
            user: The user object (optional)

        Raises:
            ValidationError: If password is invalid
        """
        raise NotImplementedError()

    def get_help_text(self) -> str:
        """Get help text for this validator."""
        return ''

    def password_changed(self, password: str, user: Any = None) -> None:
        """Called when password is changed."""
        pass


class UserAttributeSimilarityValidator(BasePasswordValidator):
    """
    Validate that password is not too similar to user attributes.

    Checks similarity between password and user attributes like
    username, email, first_name, last_name.
    """

    # Default attributes to check
    DEFAULT_USER_ATTRIBUTES = ('username', 'email', 'first_name', 'last_name')

    # Similarity threshold (0.0 - 1.0)
    max_similarity: float = 0.7

    def __init__(self, options: Dict[str, Any] = None):
        super().__init__(options)
        self.user_attributes = self.options.get('user_attributes', self.DEFAULT_USER_ATTRIBUTES)
        self.max_similarity = self.options.get('max_similarity', self.max_similarity)

    def validate(self, password: str, user: Any = None) -> None:
        if not user:
            return

        # Get user attributes
        for attr in self.user_attributes:
            value = getattr(user, attr, None)
            if not value:
                continue

            # Check similarity
            value = str(value).lower()
            password_lower = password.lower()

            # Calculate similarity
            similarity = SequenceMatcher(None, password_lower, value).quick_ratio()

            if similarity >= self.max_similarity:
                raise ValidationError(
                    [f"The password is too similar to the {attr.replace('_', ' ')}."],
                    code='password_too_similar'
                )

    def get_help_text(self) -> str:
        return "Your password can't be too similar to your other personal information."


class MinimumLengthValidator(BasePasswordValidator):
    """
    Validate that password meets minimum length requirement.
    """

    # Default minimum length
    min_length: int = 8

    def __init__(self, options: Dict[str, Any] = None):
        super().__init__(options)
        self.min_length = self.options.get('min_length', self.min_length)

    def validate(self, password: str, user: Any = None) -> None:
        if len(password) < self.min_length:
            raise ValidationError(
                [f"This password is too short. It must contain at least {self.min_length} characters."],
                code='password_too_short'
            )

    def get_help_text(self) -> str:
        return f"Your password must contain at least {self.min_length} characters."


class MaximumLengthValidator(BasePasswordValidator):
    """
    Validate that password doesn't exceed maximum length.
    """

    # Default maximum length
    max_length: int = 128

    def __init__(self, options: Dict[str, Any] = None):
        super().__init__(options)
        self.max_length = self.options.get('max_length', self.max_length)

    def validate(self, password: str, user: Any = None) -> None:
        if len(password) > self.max_length:
            raise ValidationError(
                [f"This password is too long. It must contain at most {self.max_length} characters."],
                code='password_too_long'
            )

    def get_help_text(self) -> str:
        return f"Your password must contain at most {self.max_length} characters."


class CommonPasswordValidator(BasePasswordValidator):
    """
    Validate that password is not a common password.

    Checks against a list of the most common passwords.
    """

    # List of common passwords (partial list)
    COMMON_PASSWORDS = {
        'password', '123456', '12345678', 'qwerty', 'abc123',
        'monkey', '1234567', 'letmein', 'trustno1', 'dragon',
        'baseball', 'iloveyou', 'master', 'sunshine', 'ashley',
        'bailey', 'passw0rd', 'shadow', '123123', '654321',
        'superman', 'qazwsx', 'michael', 'football', 'password1',
        'password123', 'welcome', 'admin', 'login', 'starwars',
        'hello', 'charlie', 'donald', 'loveme', 'batman',
        'qwerty123', 'qwertyuiop', 'solo', 'princess', 'azerty',
        'soccer', 'summer', 'flower', 'winter', 'spring',
    }

    def __init__(self, options: Dict[str, Any] = None):
        super().__init__(options)
        # Load additional passwords from file if provided
        password_file = self.options.get('password_list_path')
        if password_file:
            try:
                with open(password_file, 'r') as f:
                    for line in f:
                        self.COMMON_PASSWORDS.add(line.strip().lower())
            except FileNotFoundError:
                pass

    def validate(self, password: str, user: Any = None) -> None:
        if password.lower() in self.COMMON_PASSWORDS:
            raise ValidationError(
                ["This password is too common."],
                code='password_too_common'
            )

    def get_help_text(self) -> str:
        return "Your password can't be a commonly used password."


class NumericPasswordValidator(BasePasswordValidator):
    """
    Validate that password is not entirely numeric.
    """

    def validate(self, password: str, user: Any = None) -> None:
        if password.isdigit():
            raise ValidationError(
                ["This password is entirely numeric."],
                code='password_entirely_numeric'
            )

    def get_help_text(self) -> str:
        return "Your password can't be entirely numeric."


class ComplexityValidator(BasePasswordValidator):
    """
    Validate password complexity requirements.

    Requires password to contain:
    - Uppercase letters
    - Lowercase letters
    - Numbers
    - Special characters
    """

    # Default requirements
    REQUIRE_UPPERCASE = True
    REQUIRE_LOWERCASE = True
    REQUIRE_DIGIT = True
    REQUIRE_SPECIAL = True

    # Special characters
    SPECIAL_CHARS = '!@#$%^&*()_+-=[]{}|;:,.<>?'

    def __init__(self, options: Dict[str, Any] = None):
        super().__init__(options)
        self.require_uppercase = self.options.get('require_uppercase', self.REQUIRE_UPPERCASE)
        self.require_lowercase = self.options.get('require_lowercase', self.REQUIRE_LOWERCASE)
        self.require_digit = self.options.get('require_digit', self.REQUIRE_DIGIT)
        self.require_special = self.options.get('require_special', self.REQUIRE_SPECIAL)
        self.special_chars = self.options.get('special_chars', self.SPECIAL_CHARS)

    def validate(self, password: str, user: Any = None) -> None:
        errors = []

        if self.require_uppercase and not any(c.isupper() for c in password):
            errors.append("Password must contain at least one uppercase letter.")

        if self.require_lowercase and not any(c.islower() for c in password):
            errors.append("Password must contain at least one lowercase letter.")

        if self.require_digit and not any(c.isdigit() for c in password):
            errors.append("Password must contain at least one digit.")

        if self.require_special and not any(c in self.special_chars for c in password):
            errors.append(f"Password must contain at least one special character ({self.special_chars}).")

        if errors:
            raise ValidationError(errors, code='password_complexity')

    def get_help_text(self) -> str:
        requirements = []

        if self.require_uppercase:
            requirements.append("at least one uppercase letter")
        if self.require_lowercase:
            requirements.append("at least one lowercase letter")
        if self.require_digit:
            requirements.append("at least one digit")
        if self.require_special:
            requirements.append("at least one special character")

        if requirements:
            return "Your password must contain " + ", ".join(requirements) + "."
        return ""


class NoRepeatingCharactersValidator(BasePasswordValidator):
    """
    Validate that password doesn't have repeating characters.
    """

    max_repeat: int = 3

    def __init__(self, options: Dict[str, Any] = None):
        super().__init__(options)
        self.max_repeat = self.options.get('max_repeat', self.max_repeat)

    def validate(self, password: str, user: Any = None) -> None:
        # Check for repeating characters (e.g., 'aaa' or '1111')
        for i in range(len(password) - self.max_repeat + 1):
            if len(set(password[i:i + self.max_repeat])) == 1:
                raise ValidationError(
                    [f"Password must not contain {self.max_repeat} or more repeating characters."],
                    code='password_repeating_characters'
                )

    def get_help_text(self) -> str:
        return f"Your password must not contain {self.max_repeat} or more repeating characters."


class NoSequentialCharactersValidator(BasePasswordValidator):
    """
    Validate that password doesn't have sequential characters.
    """

    SEQUENCES = [
        'abcdefghijklmnopqrstuvwxyz',
        'qwertyuiop',
        'asdfghjkl',
        'zxcvbnm',
        '01234567890',
    ]

    min_sequence_length: int = 4

    def __init__(self, options: Dict[str, Any] = None):
        super().__init__(options)
        self.min_sequence_length = self.options.get('min_sequence_length', self.min_sequence_length)

    def validate(self, password: str, user: Any = None) -> None:
        password_lower = password.lower()

        for sequence in self.SEQUENCES:
            for i in range(len(sequence) - self.min_sequence_length + 1):
                subsequence = sequence[i:i + self.min_sequence_length]
                if subsequence in password_lower:
                    raise ValidationError(
                        ["Password must not contain sequential characters."],
                        code='password_sequential_characters'
                    )

                # Also check reverse
                if subsequence[::-1] in password_lower:
                    raise ValidationError(
                        ["Password must not contain sequential characters."],
                        code='password_sequential_characters'
                    )

    def get_help_text(self) -> str:
        return "Your password must not contain sequential characters (e.g., 'abcd' or '1234')."


# Default validators (like Django)
DEFAULT_PASSWORD_VALIDATORS = [
    UserAttributeSimilarityValidator,
    MinimumLengthValidator,
    CommonPasswordValidator,
    NumericPasswordValidator,
]


def validate_password(
    password: str,
    user: Any = None,
    validators: List[Type[BasePasswordValidator]] = None,
    validator_options: Dict[str, Dict] = None
) -> List[str]:
    """
    Validate password using all validators.

    Args:
        password: The password to validate
        user: The user object (optional)
        validators: List of validator classes (defaults to DEFAULT_PASSWORD_VALIDATORS)
        validator_options: Dict mapping validator class names to their options

    Returns:
        List of error messages (empty if valid)

    Example:
        errors = validate_password('weak', user=current_user)
        if errors:
            print("Password invalid:", errors)
    """
    if validators is None:
        validators = DEFAULT_PASSWORD_VALIDATORS

    validator_options = validator_options or {}
    errors = []

    for validator_class in validators:
        # Get options for this validator
        options = validator_options.get(validator_class.__name__, {})
        validator = validator_class(options)

        try:
            validator.validate(password, user)
        except ValidationError as e:
            errors.extend(e.messages)

    return errors


def get_password_validators_help_text(validators: List[Type[BasePasswordValidator]] = None) -> str:
    """
    Get help text for all validators.

    Args:
        validators: List of validator classes

    Returns:
        Combined help text string
    """
    if validators is None:
        validators = DEFAULT_PASSWORD_VALIDATORS

    help_texts = []
    for validator_class in validators:
        validator = validator_class()
        help_text = validator.get_help_text()
        if help_text:
            help_texts.append(help_text)

    return '\n'.join(help_texts)
