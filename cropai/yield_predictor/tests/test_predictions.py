"""
yield_predictor/test_predictions.py - Tests for prediction endpoints
"""
import pytest
from unittest.mock import patch
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken


@pytest.mark.django_db
@pytest.mark.predictions
class TestPredictionListCreate:
    """Tests for GET/POST /api/v1/predictions/"""

    def test_list_predictions_authenticated(self, authenticated_client, test_user):
        """Test listing predictions requires authentication."""
        response = authenticated_client.get('/api/v1/predictions/')
        
        assert response.status_code == status.HTTP_200_OK
        assert isinstance(response.data, (list, dict))  # May be paginated

    def test_list_predictions_unauthenticated_fails(self, api_client):
        """Test listing predictions without authentication fails."""
        response = api_client.get('/api/v1/predictions/')
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_list_predictions_only_own(self, api_client, test_user, another_user):
        """Test user only sees their own predictions."""
        from yield_predictor.models import YieldPrediction
        
        # Create predictions for both users
        YieldPrediction.objects.create(
            user=test_user,
            crop='maize',
            location='Nakuru',
            planting_date='2026-01-01',
            predicted_yield=5.5,
            harvest_window='June 2026',
            net_profit=50000,
            rainfall=600,
            temperature=22,
            humidity=65
        )
        YieldPrediction.objects.create(
            user=another_user,
            crop='beans',
            location='Kisii',
            planting_date='2026-01-01',
            predicted_yield=2.0,
            harvest_window='May 2026',
            net_profit=20000,
            rainfall=700,
            temperature=20,
            humidity=70
        )
        
        # Authenticate as test_user
        refresh = RefreshToken.for_user(test_user)
        api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
        
        response = api_client.get('/api/v1/predictions/')
        
        assert response.status_code == status.HTTP_200_OK
        # Verify viewing only own predictions
        if isinstance(response.data, list):
            for pred in response.data:
                assert pred['user_email'] == test_user.email

    def test_create_prediction_success(self, authenticated_client, test_user):
        """Test creating a prediction via the API (mocks the ML pipeline)."""
        data = {
            'crop': 'maize',
            'location': 'Nakuru',
            'planting_date': '2026-01-01',
            'soil_ph': 6.0,
            'soil_moisture': 25.0,
            'organic_carbon': 1.5,
            'fertilizer_kg_ha': 100.0,
        }

        mock_result = {
            'success': True,
            'predicted_yield': 5.5,
            'yield_range': [4.68, 6.33],
            'harvest_window': 'May 21, 2026 to June 10, 2026',
            'net_profit': 167500.0,
            'weather_data': {'temp': 22.0, 'rainfall': 800.0, 'humidity': 65.0},
            'ai_recommendations': ['Apply fertilizer early'],
            'risk_level': 'low',
            'risk_reason': 'Good growing conditions',
            'fallback_used': False,
        }

        with patch('yield_predictor.views.run_prediction', return_value=mock_result):
            response = authenticated_client.post('/api/v1/predictions/', data, format='json')

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['crop'] == 'maize'
        assert response.data['user_email'] == test_user.email

    def test_create_prediction_unauthenticated_fails(self, api_client):
        """Test creating prediction without authentication fails."""
        data = {
            'crop': 'maize',
            'location': 'Nakuru',
            'planting_date': '2026-01-01',
            'soil_ph': 6.0,
            'soil_moisture': 25.0,
            'organic_carbon': 1.5,
            'fertilizer_kg_ha': 100.0,
        }
        
        response = api_client.post('/api/v1/predictions/', data, format='json')
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_create_prediction_missing_fields(self, authenticated_client):
        """Test creating prediction with missing required fields."""
        data = {
            'crop': 'maize',
            'location': 'Nakuru'
            # Missing required planting_date
        }
        
        response = authenticated_client.post('/api/v1/predictions/', data, format='json')
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST

@pytest.mark.django_db
@pytest.mark.predictions
class TestPredictionDetail:
    """Tests for GET/DELETE /api/v1/predictions/{id}/"""

    def test_get_prediction_success(self, authenticated_client, test_user):
        """Test retrieving a prediction."""
        from yield_predictor.models import YieldPrediction
        
        prediction = YieldPrediction.objects.create(
            user=test_user,
            crop='maize',
            location='Nakuru',
            planting_date='2026-01-01',
            predicted_yield=5.5,
            harvest_window='June 2026',
            net_profit=50000,
            rainfall=600,
            temperature=22,
            humidity=65
        )
        
        response = authenticated_client.get(f'/api/v1/predictions/{prediction.id}/')
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['id'] == prediction.id
        assert response.data['crop'] == 'maize'

    def test_get_prediction_not_found(self, authenticated_client):
        """Test retrieving non-existent prediction."""
        response = authenticated_client.get('/api/v1/predictions/99999/')
        
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_get_other_user_prediction_fails(self, api_client, test_user, another_user):
        """Test user cannot see another user's prediction."""
        from yield_predictor.models import YieldPrediction
        
        prediction = YieldPrediction.objects.create(
            user=another_user,
            crop='beans',
            location='Kisii',
            planting_date='2026-01-01',
            predicted_yield=2.0,
            harvest_window='May 2026',
            net_profit=20000,
            rainfall=700,
            temperature=20,
            humidity=70
        )
        
        refresh = RefreshToken.for_user(test_user)
        api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
        
        response = api_client.get(f'/api/v1/predictions/{prediction.id}/')
        
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_delete_prediction_success(self, authenticated_client, test_user):
        """Test deleting a prediction."""
        from yield_predictor.models import YieldPrediction
        
        prediction = YieldPrediction.objects.create(
            user=test_user,
            crop='maize',
            location='Nakuru',
            planting_date='2026-01-01',
            predicted_yield=5.5,
            harvest_window='June 2026',
            net_profit=50000,
            rainfall=600,
            temperature=22,
            humidity=65
        )
        
        response = authenticated_client.delete(f'/api/v1/predictions/{prediction.id}/')
        
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not YieldPrediction.objects.filter(id=prediction.id).exists()

    def test_delete_other_user_prediction_fails(self, api_client, test_user, another_user):
        """Test user cannot delete another user's prediction."""
        from yield_predictor.models import YieldPrediction
        
        prediction = YieldPrediction.objects.create(
            user=another_user,
            crop='beans',
            location='Kisii',
            planting_date='2026-01-01',
            predicted_yield=2.0,
            harvest_window='May 2026',
            net_profit=20000,
            rainfall=700,
            temperature=20,
            humidity=70
        )
        
        refresh = RefreshToken.for_user(test_user)
        api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
        
        response = api_client.delete(f'/api/v1/predictions/{prediction.id}/')
        
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_delete_prediction_unauthenticated_fails(self, api_client, test_user):
        """Test deleting prediction without authentication fails."""
        from yield_predictor.models import YieldPrediction
        
        prediction = YieldPrediction.objects.create(
            user=test_user,
            crop='maize',
            location='Nakuru',
            planting_date='2026-01-01',
            predicted_yield=5.5,
            harvest_window='June 2026',
            net_profit=50000,
            rainfall=600,
            temperature=22,
            humidity=65
        )
        
        response = api_client.delete(f'/api/v1/predictions/{prediction.id}/')
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
