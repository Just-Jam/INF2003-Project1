# core/utils.py
from django.contrib.auth import get_user_model
from rest_framework.authtoken.models import Token

User = get_user_model()


class AuthHelper:
    @staticmethod
    def create_user_response(user):
        """Create standardized user response with token"""
        token, _ = Token.objects.get_or_create(user=user)
        return {
            "user_id": user.user_id,
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "token": token.key,
        }

    @staticmethod
    def validate_password_strength(password):
        """Enhanced password validation"""
        if len(password) < 8:
            return False, "Password must be at least 8 characters long"
        if not any(char.isdigit() for char in password):
            return False, "Password must contain at least one number"
        if not any(char.isalpha() for char in password):
            return False, "Password must contain at least one letter"
        return True, "Password is strong"