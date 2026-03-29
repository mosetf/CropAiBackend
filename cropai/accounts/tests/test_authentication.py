"""
accounts/test_authentication.py - Tests for authentication endpoints
"""
import pytest
from django.contrib.auth.models import User
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken


@pytest.mark.django_db
@pytest.mark.auth
class TestLoginView:
    """Tests for POST /api/v1/auth/login/"""

    def test_login_success(self, api_client):
        """Test successful login returns access token and user."""
        User.objects.create_user(username='testuser_auto', email='test@example.com', password='testpass123')
        
        response = api_client.post('/api/v1/auth/login/', {
            'email': 'test@example.com',
            'password': 'testpass123',
            'remember_me': False
        }, format='json')
        
        assert response.status_code == status.HTTP_200_OK
        assert 'access' in response.data
        assert 'user' in response.data
        assert response.data['user']['email'] == 'test@example.com'

    def test_login_invalid_credentials(self, api_client):
        """Test login with invalid credentials fails."""
        User.objects.create_user(username='testuser_auto', email='test@example.com', password='testpass123')
        
        response = api_client.post('/api/v1/auth/login/', {
            'email': 'test@example.com',
            'password': 'wrongpassword'
        }, format='json')
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert 'detail' in response.data

    def test_login_nonexistent_user(self, api_client):
        """Test login with non-existent user fails."""
        response = api_client.post('/api/v1/auth/login/', {
            'email': 'nonexistent@example.com',
            'password': 'anypassword'
        }, format='json')
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_login_sets_refresh_cookie(self, api_client):
        """Test login sets refresh token in httpOnly cookie."""
        User.objects.create_user(username='testuser_auto', email='test@example.com', password='testpass123')
        
        response = api_client.post('/api/v1/auth/login/', {
            'email': 'test@example.com',
            'password': 'testpass123'
        }, format='json')
        
        assert response.status_code == status.HTTP_200_OK
        assert 'cropai_refresh' in response.cookies

    def test_login_remember_me_creates_session(self, api_client):
        """Test login with remember_me creates UserSession."""
        from accounts.models import UserSession
        
        user = User.objects.create_user(username='testuser_auto', email='test@example.com', password='testpass123')
        
        response = api_client.post('/api/v1/auth/login/', {
            'email': 'test@example.com',
            'password': 'testpass123',
            'remember_me': True
        }, format='json')
        
        assert response.status_code == status.HTTP_200_OK
        assert UserSession.objects.filter(user=user).exists()

    def test_login_missing_credentials(self, api_client):
        """Test login with missing credentials fails."""
        response = api_client.post('/api/v1/auth/login/', {
            'email': 'test@example.com'
        }, format='json')
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST

@pytest.mark.django_db
@pytest.mark.auth
class TestLogoutView:
    """Tests for POST /api/v1/auth/logout/"""

    def test_logout_success(self, authenticated_client):
        """Test successful logout."""
        response = authenticated_client.post('/api/v1/auth/logout/')
        
        assert response.status_code == status.HTTP_200_OK
        assert 'detail' in response.data

    def test_logout_unauthenticated_fails(self, api_client):
        """Test logout without authentication fails."""
        response = api_client.post('/api/v1/auth/logout/')
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_logout_deletes_session(self, authenticated_client, test_user):
        """Test logout deletes UserSession."""
        from accounts.models import UserSession
        
        # Create a session first by logging in
        refresh = RefreshToken.for_user(test_user)
        UserSession.objects.create(
            user=test_user,
            jti=str(refresh['jti']),
            expires_at='2099-12-31T23:59:59Z'
        )
        
        # Get refresh token from cookie
        authenticated_client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
        authenticated_client.cookies['cropai_refresh'] = str(refresh)
        
        response = authenticated_client.post('/api/v1/auth/logout/')
        
        assert response.status_code == status.HTTP_200_OK

@pytest.mark.django_db
@pytest.mark.auth
class TestRefreshTokenView:
    """Tests for POST /api/v1/auth/refresh/"""

    def test_refresh_token_success(self, api_client, test_user):
        """Test successful token refresh."""
        refresh = RefreshToken.for_user(test_user)
        from accounts.models import UserSession
        
        UserSession.objects.create(
            user=test_user,
            jti=str(refresh['jti']),
            expires_at='2099-12-31T23:59:59Z'
        )
        
        api_client.cookies['cropai_refresh'] = str(refresh)
        
        response = api_client.post('/api/v1/auth/refresh/')
        
        assert response.status_code == status.HTTP_200_OK
        assert 'access' in response.data

    def test_refresh_no_token_fails(self, api_client):
        """Test refresh without token fails."""
        response = api_client.post('/api/v1/auth/refresh/')
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_refresh_invalid_token_fails(self, api_client):
        """Test refresh with invalid token fails."""
        api_client.cookies['cropai_refresh'] = 'invalid.token.here'
        
        response = api_client.post('/api/v1/auth/refresh/')
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

@pytest.mark.django_db
@pytest.mark.auth
class TestCurrentUserView:
    """Tests for GET /api/v1/auth/user/"""

    def test_get_current_user_success(self, authenticated_client, test_user):
        """Test getting current user info."""
        response = authenticated_client.get('/api/v1/auth/user/')
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['email'] == test_user.email
        assert 'username' not in response.data

    def test_get_current_user_unauthenticated_fails(self, api_client):
        """Test getting user without authentication fails."""
        response = api_client.get('/api/v1/auth/user/')
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
