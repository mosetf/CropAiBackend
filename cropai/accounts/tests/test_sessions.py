"""
accounts/test_sessions.py - Tests for session management endpoints
"""
import pytest
from django.contrib.auth.models import User
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken


@pytest.mark.django_db
@pytest.mark.sessions
class TestSessionListView:
    """Tests for GET /api/v1/auth/sessions/"""

    def test_list_sessions_success(self, authenticated_client, test_user):
        """Test listing user's active sessions."""
        from accounts.models import UserSession
        
        refresh = RefreshToken.for_user(test_user)
        UserSession.objects.create(
            user=test_user,
            jti=str(refresh['jti']),
            device_name='Test Device',
            browser='Chrome',
            os='Windows',
            ip_address='127.0.0.1',
            expires_at='2099-12-31T23:59:59Z'
        )
        
        response = authenticated_client.get('/api/v1/auth/sessions/')
        
        assert response.status_code == status.HTTP_200_OK
        assert isinstance(response.data, list)
        assert len(response.data) >= 1

    def test_list_sessions_contains_device_info(self, authenticated_client, test_user):
        """Test session list includes device information."""
        from accounts.models import UserSession
        
        refresh = RefreshToken.for_user(test_user)
        UserSession.objects.create(
            user=test_user,
            jti=str(refresh['jti']),
            device_name='iPhone',
            browser='Safari',
            os='iOS',
            ip_address='192.168.1.1',
            expires_at='2099-12-31T23:59:59Z'
        )
        
        response = authenticated_client.get('/api/v1/auth/sessions/')
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data[0]['device_name'] == 'iPhone'
        assert response.data[0]['browser'] == 'Safari'
        assert response.data[0]['os'] == 'iOS'

    def test_list_sessions_unauthenticated_fails(self, api_client):
        """Test listing sessions without authentication fails."""
        response = api_client.get('/api/v1/auth/sessions/')
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_list_sessions_only_shows_own(self, api_client, test_user, another_user):
        """Test user only sees their own sessions."""
        from accounts.models import UserSession
        
        # Create sessions for both users
        refresh_test = RefreshToken.for_user(test_user)
        refresh_other = RefreshToken.for_user(another_user)
        
        UserSession.objects.create(
            user=test_user,
            jti=str(refresh_test['jti']),
            device_name='Device 1',
            expires_at='2099-12-31T23:59:59Z'
        )
        UserSession.objects.create(
            user=another_user,
            jti=str(refresh_other['jti']),
            device_name='Device 2',
            expires_at='2099-12-31T23:59:59Z'
        )
        
        # Authenticate as test_user
        api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh_test.access_token}')
        response = api_client.get('/api/v1/auth/sessions/')
        
        assert response.status_code == status.HTTP_200_OK
        # Should only see their own session
        assert all(session['device_name'] != 'Device 2' for session in response.data)


@pytest.mark.django_db
@pytest.mark.sessions
class TestSessionRevokeView:
    """Tests for DELETE /api/v1/auth/sessions/"""

    def test_revoke_specific_session(self, authenticated_client, test_user):
        """Test revoking a specific session by ID."""
        from accounts.models import UserSession
        
        refresh = RefreshToken.for_user(test_user)
        session = UserSession.objects.create(
            user=test_user,
            jti=str(refresh['jti']),
            device_name='Device to Revoke',
            expires_at='2099-12-31T23:59:59Z'
        )
        
        response = authenticated_client.delete(f'/api/v1/auth/sessions/?id={session.id}')
        
        assert response.status_code == status.HTTP_200_OK
        assert not UserSession.objects.filter(id=session.id).exists()

    def test_revoke_nonexistent_session_fails(self, authenticated_client):
        """Test revoking non-existent session fails."""
        response = authenticated_client.delete('/api/v1/auth/sessions/?id=99999')
        
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_revoke_all_other_sessions(self, authenticated_client, test_user):
        """Test revoking all other sessions."""
        from accounts.models import UserSession
        
        refresh1 = RefreshToken.for_user(test_user)
        refresh2 = RefreshToken.for_user(test_user)
        
        session1 = UserSession.objects.create(
            user=test_user,
            jti=str(refresh1['jti']),
            device_name='Device 1',
            expires_at='2099-12-31T23:59:59Z'
        )
        session2 = UserSession.objects.create(
            user=test_user,
            jti=str(refresh2['jti']),
            device_name='Device 2',
            expires_at='2099-12-31T23:59:59Z'
        )
        
        # Set current session
        authenticated_client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh1.access_token}')
        authenticated_client.cookies['cropai_refresh'] = str(refresh1)
        
        response = authenticated_client.delete('/api/v1/auth/sessions/')
        
        assert response.status_code == status.HTTP_200_OK
        # Current session should still exist
        assert UserSession.objects.filter(id=session1.id).exists()
        # Other sessions should be deleted
        assert not UserSession.objects.filter(id=session2.id).exists()

    def test_revoke_other_user_session_fails(self, api_client, test_user, another_user):
        """Test user cannot revoke another user's session."""
        from accounts.models import UserSession
        
        refresh_test = RefreshToken.for_user(test_user)
        refresh_other = RefreshToken.for_user(another_user)
        
        other_session = UserSession.objects.create(
            user=another_user,
            jti=str(refresh_other['jti']),
            device_name='Other Device',
            expires_at='2099-12-31T23:59:59Z'
        )
        
        api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh_test.access_token}')
        response = api_client.delete(f'/api/v1/auth/sessions/?id={other_session.id}')
        
        # Should return 404 since user cannot see/revoke other user's sessions
        assert response.status_code == status.HTTP_404_NOT_FOUND
        # Other user's session should still exist
        assert UserSession.objects.filter(id=other_session.id).exists()

    def test_revoke_unauthenticated_fails(self, api_client):
        """Test revoking sessions without authentication fails."""
        response = api_client.delete('/api/v1/auth/sessions/')
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
