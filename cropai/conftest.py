import pytest
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken


@pytest.fixture
def api_client():
    """Return an API client instance."""
    return APIClient()


@pytest.fixture
def test_user(db):
    """Create a test user."""
    user = User.objects.create_user(
        username='testuser',
        email='test@example.com',
        password='testpass123'
    )
    return user


@pytest.fixture
def authenticated_client(api_client, test_user):
    """Return an API client with JWT authentication."""
    refresh = RefreshToken.for_user(test_user)
    api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
    return api_client


@pytest.fixture
def user_with_token(db):
    """Create user and return with refresh token."""
    user = User.objects.create_user(
        username='testuser2',
        email='test2@example.com',
        password='testpass123'
    )
    refresh = RefreshToken.for_user(user)
    return {
        'user': user,
        'refresh': str(refresh),
        'access': str(refresh.access_token)
    }


@pytest.fixture
def another_user(db):
    """Create a different test user."""
    return User.objects.create_user(
        username='otheruser',
        email='other@example.com',
        password='otherpass123'
    )
