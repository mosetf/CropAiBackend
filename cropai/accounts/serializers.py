"""
accounts/serializers.py - DRF serializers for authentication and session management
"""
from rest_framework import serializers
from django.contrib.auth.models import User
from .models import UserSession


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'first_name', 'last_name')
        read_only_fields = ('id',)


class LoginSerializer(serializers.Serializer):
    """Serializer for login endpoint"""
    username = serializers.CharField(write_only=True)
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
