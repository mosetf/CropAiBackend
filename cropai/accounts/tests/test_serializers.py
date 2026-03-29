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
        from cropai.accounts.serializers import UserSerializer
        
        serializer = UserSerializer(test_user)
        
        assert serializer.data['id'] == test_user.id
        assert serializer.data['username'] == test_user.username
        assert serializer.data['email'] == test_user.email
        assert serializer.data['first_name'] == test_user.first_name

    def test_serialize_user_excludes_password(self, test_user):
        """Test password is not serialized."""
        from cropai.accounts.serializers import UserSerializer
        
        serializer = UserSerializer(test_user)
        
        assert 'password' not in serializer.data

    def test_user_serializer_read_only_fields(self, test_user):
        """Test read-only fields cannot be updated."""
        from cropai.accounts.serializers import UserSerializer
        
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
        from cropai.accounts.serializers import LoginSerializer
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

    def test_validate_credentials_wrong_password(self, test_user):
        """Test validating with wrong password fails."""
        from cropai.accounts.serializers import LoginSerializer
        
        data = {
            'username': test_user.username,
            'password': 'wrongpassword',
            'remember_me': False
        }
        
        serializer = LoginSerializer(data=data)
        
        assert not serializer.is_valid()
        assert 'non_field_errors' in serializer.errors

    def test_validate_credentials_user_not_found(self):
        """Test validating with non-existent user fails."""
        from cropai.accounts.serializers import LoginSerializer
        
        data = {
            'username': 'nonexistent',
            'password': 'somepassword',
            'remember_me': False
        }
        
        serializer = LoginSerializer(data=data)
        
        assert not serializer.is_valid()

    def test_remember_me_flag_included(self):
        """Test remember_me flag is processed."""
        from cropai.accounts.serializers import LoginSerializer
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

@pytest.mark.django_db
@pytest.mark.serializers
class TestTokenPairSerializer:
    """Tests for TokenPairSerializer (access + refresh token)"""

    def test_serializer_includes_tokens(self, test_user):
        """Test serializer returns access and refresh tokens."""
        from cropai.accounts.serializers import TokenPairSerializer
        
        serializer = TokenPairSerializer(test_user)
        
        assert 'access' in serializer.data
        assert 'refresh' in serializer.data
        assert serializer.data['access'] is not None
        assert serializer.data['refresh'] is not None

    def test_serializer_tokens_are_strings(self, test_user):
        """Test tokens are valid JWT strings."""
        from cropai.accounts.serializers import TokenPairSerializer
        
        serializer = TokenPairSerializer(test_user)
        
        access = serializer.data['access']
        refresh = serializer.data['refresh']
        
        assert isinstance(access, str)
        assert isinstance(refresh, str)
        assert len(access) > 0
        assert len(refresh) > 0
