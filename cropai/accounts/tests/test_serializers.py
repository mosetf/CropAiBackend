"""
accounts/test_serializers.py - Tests for account serializers
"""
import pytest
from django.contrib.auth.models import User


@pytest.mark.django_db
@pytest.mark.serializers
class TestUserSerializer:
    """Tests for UserSerializer"""

    def test_serialize_user(self, test_user):
        """Test serializing a user."""
        from accounts.serializers import UserSerializer
        
        serializer = UserSerializer(test_user)
        
        assert serializer.data['id'] == test_user.id
        assert serializer.data['username'] == test_user.username
        assert serializer.data['email'] == test_user.email
        assert serializer.data['first_name'] == test_user.first_name

    def test_serialize_user_excludes_password(self, test_user):
        """Test password is not serialized."""
        from accounts.serializers import UserSerializer
        
        serializer = UserSerializer(test_user)
        
        assert 'password' not in serializer.data

    def test_user_serializer_read_only_fields(self, test_user):
        """Test read-only fields cannot be updated."""
        from accounts.serializers import UserSerializer
        
        data = {
            'username': 'newusername',
            'email': 'newemail@test.com',
            'id': 999
        }
        
        serializer = UserSerializer(test_user, data=data, partial=True)
        
        assert serializer.is_valid()
        serializer.save()
        
        # ID should not change
        assert test_user.id != 999

@pytest.mark.django_db
@pytest.mark.serializers
class TestLoginSerializer:
    """Tests for LoginSerializer"""

    def test_validate_credentials_success(self):
        """Test validating correct credentials."""
        from accounts.serializers import LoginSerializer
        from django.contrib.auth.models import User
        
        user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        
        data = {
            'username': 'testuser',
            'password': 'testpass123',
            'remember_me': False
        }
        
        serializer = LoginSerializer(data=data)
        assert serializer.is_valid()

    def test_remember_me_flag_included(self):
        """Test remember_me flag is processed."""
        from accounts.serializers import LoginSerializer
        from django.contrib.auth.models import User
        
        user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        
        data = {
            'username': 'testuser',
            'password': 'testpass123',
            'remember_me': True
        }
        
        serializer = LoginSerializer(data=data)
        assert serializer.is_valid()
        assert serializer.validated_data['remember_me'] == True


