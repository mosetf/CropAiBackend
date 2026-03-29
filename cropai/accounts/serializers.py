"""
accounts/serializers.py - DRF serializers for authentication and session management
"""
from rest_framework import serializers
from django.contrib.auth.models import User
from django.core.validators import EmailValidator
from django.contrib.auth import get_user_model
import uuid
from .models import UserSession


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'email', 'first_name', 'last_name')
        read_only_fields = ('id',)


class LoginSerializer(serializers.Serializer):
    """Serializer for login endpoint - email based"""
    email = serializers.EmailField(write_only=True)
    password = serializers.CharField(write_only=True, style={'input_type': 'password'})
    remember_me = serializers.BooleanField(required=False, default=False)
    
    access = serializers.SerializerMethodField()
    user = UserSerializer(read_only=True)
    
    def get_access(self, obj):
        return None


class UserSessionSerializer(serializers.ModelSerializer):
    is_current = serializers.SerializerMethodField()
    
    class Meta:
        model = UserSession
        fields = (
            'id', 'device_name', 'device_type', 'browser', 'os', 
            'ip_address', 'created_at', 'last_active', 'is_current'
        )
        read_only_fields = fields
    
    def get_is_current(self, obj):
        request = self.context.get('request')
        if not request:
            return False
        from rest_framework_simplejwt.tokens import RefreshToken
        try:
            refresh_cookie = request.COOKIES.get('cropai_refresh')
            if refresh_cookie:
                jti = str(RefreshToken(refresh_cookie)['jti'])
                return obj.jti == jti
        except Exception:
            pass
        return False


class RegisterSerializer(serializers.Serializer):
    """Serializer for user registration endpoint - email based"""
    email = serializers.EmailField(
        required=True,
        validators=[EmailValidator()],
        help_text="Valid email address (used for login)"
    )
    password = serializers.CharField(
        write_only=True,
        required=True,
        min_length=8,
        style={'input_type': 'password'},
        help_text="Password (minimum 8 characters)"
    )
    password_confirm = serializers.CharField(
        write_only=True,
        required=True,
        style={'input_type': 'password'},
        help_text="Confirm password (must match password)"
    )
    first_name = serializers.CharField(
        max_length=150,
        required=False,
        allow_blank=True,
        help_text="First name (optional)"
    )
    last_name = serializers.CharField(
        max_length=150,
        required=False,
        allow_blank=True,
        help_text="Last name (optional)"
    )
    
    user = UserSerializer(read_only=True)
    access = serializers.CharField(read_only=True)
    
    def validate_email(self, value):
        """Check if email is unique"""
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Email already exists")
        return value
    
    def validate(self, data):
        """Check if passwords match"""
        if data.get('password') != data.get('password_confirm'):
            raise serializers.ValidationError({
                'password_confirm': "Passwords do not match"
            })
        return data
