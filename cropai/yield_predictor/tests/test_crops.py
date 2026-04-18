"""
yield_predictor/test_crops.py - Tests for crop endpoints
"""
import pytest
from rest_framework import status


@pytest.mark.django_db
@pytest.mark.crops
class TestCropListView:
    """Tests for GET /api/v1/crops/"""

    def test_list_crops_success(self, api_client):
        """Test listing crops doesn't require authentication."""
        response = api_client.get('/api/v1/crops/')
        
        assert response.status_code == status.HTTP_200_OK
        assert isinstance(response.data, (list, dict))

    def test_list_crops_structure(self, api_client):
        """Test crop list contains required fields."""
        from yield_predictor.models import CropModel
        
        CropModel.objects.create(
            crop='maize',
            file_path='/path/to/model',
            r2_score=0.85,
            mae=0.12,
            is_active=True
        )
        
        response = api_client.get('/api/v1/crops/')
        
        assert response.status_code == status.HTTP_200_OK
        if response.data:  # Check if list has items
            crop = response.data[0]
            assert 'id' in crop
            assert 'crop' in crop
            assert 'r2_score' in crop
            assert 'mae' in crop
            assert 'is_active' in crop

    def test_list_crops_only_active(self, api_client):
        """Test only active crops are returned."""
        from yield_predictor.models import CropModel
        
        # Create active crop
        active = CropModel.objects.create(
            crop='maize',
            file_path='/path/to/model',
            r2_score=0.85,
            is_active=True
        )
        
        # Create inactive crop
        inactive = CropModel.objects.create(
            crop='wheat',
            file_path='/path/to/model',
            r2_score=0.80,
            is_active=False
        )
        
        response = api_client.get('/api/v1/crops/')
        
        assert response.status_code == status.HTTP_200_OK
        crop_ids = [crop['id'] for crop in response.data]
        assert active.id in crop_ids
        assert inactive.id not in crop_ids

    def test_list_crops_empty(self, api_client, db):
        """Test empty crop list returns empty array."""
        # No crops created
        response = api_client.get('/api/v1/crops/')
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data == []


@pytest.mark.django_db
@pytest.mark.crops
class TestCropDetail:
    """Tests for GET /api/v1/crops/{id}/"""

    def test_get_crop_success(self, api_client):
        """Test retrieving a specific crop."""
        from yield_predictor.models import CropModel
        
        crop = CropModel.objects.create(
            crop='maize',
            file_path='/path/to/model',
            r2_score=0.85,
            mae=0.12,
            is_active=True
        )
        
        response = api_client.get(f'/api/v1/crops/{crop.id}/')
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['id'] == crop.id
        assert response.data['crop'] == 'maize'
        assert response.data['r2_score'] == 0.85

    def test_get_crop_not_found(self, api_client):
        """Test retrieving non-existent crop."""
        response = api_client.get('/api/v1/crops/99999/')
        
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_get_inactive_crop_not_found(self, api_client):
        """Test inactive crops cannot be retrieved."""
        from yield_predictor.models import CropModel
        
        crop = CropModel.objects.create(
            crop='wheat',
            file_path='/path/to/model',
            r2_score=0.80,
            is_active=False
        )
        
        response = api_client.get(f'/api/v1/crops/{crop.id}/')
        
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_crop_detail_no_auth_required(self, api_client):
        """Test accessing crop detail doesn't require authentication."""
        from yield_predictor.models import CropModel
        
        crop = CropModel.objects.create(
            crop='beans',
            file_path='/path/to/model',
            r2_score=0.75,
            is_active=True
        )
        
        # Don't set credentials
        response = api_client.get(f'/api/v1/crops/{crop.id}/')
        
        assert response.status_code == status.HTTP_200_OK
