"""
yield_predictor/views.py - DRF viewsets and API endpoints only
"""
from rest_framework import viewsets, mixins, permissions
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import ValidationError
from django.conf import settings as django_settings
from drf_spectacular.utils import extend_schema, OpenApiResponse

from .models import YieldPrediction, CropModel
from .serializers import YieldPredictionSerializer, CropModelSerializer
from .services.prediction_service import LOCATION_COORDS, run_prediction

# DRF VIEWSETS (REST API endpoints)
@extend_schema(
    tags=['Yield Prediction'],
    description='Manage yield predictions for authenticated users'
)
class YieldPredictionViewSet(
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.DestroyModelMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    """
    API endpoint for yield predictions (immutable records – no update/replace).

    list:    GET /api/v1/predictions/
             Returns paginated list of user's predictions

    create:  POST /api/v1/predictions/
             Accepts crop inputs, runs the prediction pipeline, and stores results.

    retrieve: GET /api/v1/predictions/{id}/
              Get specific prediction by ID

    destroy: DELETE /api/v1/predictions/{id}/
             Delete a prediction

    Writable inputs:
    - crop: str (maize, wheat, beans, etc)
    - location: str (Nakuru, Mombasa, etc)
    - planting_date: date (YYYY-MM-DD)
    - soil_ph: float (0-14)
    - soil_moisture: float (0-100%)
    - organic_carbon: float (%)
    - fertilizer_kg_ha: float

    Returns (server-computed, read-only):
    - predicted_yield: float (tonnes/ha)
    - yield_low/high: float (confidence interval)
    - net_profit: float (KES)
    - risk_level: str (low, medium, high)
    - ai_recommendations: list
    """
    serializer_class = YieldPredictionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return YieldPrediction.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        data = serializer.validated_data

        api_settings = {
            'api_key': getattr(django_settings, 'API_KEY', ''),
            'base_url': getattr(django_settings, 'BASE_URL', ''),
            'forecast_url': getattr(django_settings, 'FORECAST_URL', ''),
        }

        result = run_prediction(
            crop=data['crop'],
            location=data['location'],
            soil_data={
                'soil_ph': data.get('soil_ph', 6.0),
                'soil_moisture': data.get('soil_moisture', 25.0),
                'organic_carbon': data.get('organic_carbon', 1.5),
            },
            fertilizer=data.get('fertilizer_kg_ha', 100.0),
            planting_date=data['planting_date'],
            api_settings=api_settings,
        )

        if not result.get('success'):
            # Log the internal error without exposing it to the client
            import logging
            logging.getLogger(__name__).error(
                'Prediction pipeline failed for user %s: %s',
                self.request.user.pk,
                result.get('error', ''),
            )
            raise ValidationError(
                {'detail': 'Prediction could not be completed. Please check your inputs and try again.'}
            )

        loc_info = LOCATION_COORDS.get(data['location'], {})
        planting_month = data['planting_date'].month
        season = 'long_rains' if planting_month in [3, 4, 5] else 'short_rains'

        serializer.save(
            user=self.request.user,
            region=loc_info.get('region', ''),
            season=season,
            predicted_yield=result['predicted_yield'],
            yield_low=result['yield_range'][0],
            yield_high=result['yield_range'][1],
            harvest_window=result['harvest_window'],
            net_profit=result['net_profit'],
            rainfall=result['weather_data']['rainfall'],
            temperature=result['weather_data']['temp'],
            humidity=result['weather_data']['humidity'],
            ai_recommendations=result['ai_recommendations'],
            risk_level=result['risk_level'],
            risk_reason=result.get('risk_reason', ''),
            fallback_used=result.get('fallback_used', False),
        )


@extend_schema(
    tags=['Crop Models'],
    description='Available crop models for prediction'
)
class CropModelViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint for crop models (read-only).
    
    list:    GET /api/v1/crops/
             Returns available crop models with specs
    
    retrieve: GET /api/v1/crops/{id}/
              Get specific crop model details
    
    Returns crop model info:
    - name: str (display name)
    - code: str (maize, wheat, etc)
    - description: str
    - version: str (model version)
    - is_active: bool
    """
    queryset = CropModel.objects.filter(is_active=True)
    serializer_class = CropModelSerializer
    permission_classes = [permissions.AllowAny]


# META/REFERENCE DATA ENDPOINTS

@extend_schema(
    tags=['Meta'],
    summary='Get Available Locations',
    description='Returns list of all available locations for yield predictions. Use this to populate location dropdown in frontend.',
    responses={
        200: OpenApiResponse(
            description='List of locations with metadata',
            response={
                'type': 'object',
                'properties': {
                    'locations': {
                        'type': 'array',
                        'items': {
                            'type': 'object',
                            'properties': {
                                'name': {'type': 'string', 'example': 'Nairobi'},
                                'lat': {'type': 'number', 'example': -1.2864},
                                'lon': {'type': 'number', 'example': 36.8172},
                                'elevation_m': {'type': 'integer', 'example': 1795},
                                'region': {'type': 'string', 'example': 'Nairobi Metropolitan'}
                            }
                        }
                    },
                    'count': {'type': 'integer', 'example': 47}
                }
            }
        )
    }
)
@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def get_locations(request):
    """
    GET /api/v1/meta/locations/
    
    Returns all available locations for predictions with their coordinates and region info.
    Frontend should use this to populate location dropdowns.
    
    Response format:
    {
        "locations": [
            {
                "name": "Nairobi",
                "lat": -1.2864,
                "lon": 36.8172,
                "elevation_m": 1795,
                "region": "Nairobi Metropolitan"
            },
            ...
        ],
        "count": 47
    }
    """
    locations_list = [
        {
            'name': name,
            'lat': data['lat'],
            'lon': data['lon'],
            'elevation_m': data['elevation_m'],
            'region': data['region']
        }
        for name, data in sorted(LOCATION_COORDS.items())
    ]
    
    return Response({
        'locations': locations_list,
        'count': len(locations_list)
    })


@extend_schema(
    tags=['Meta'],
    summary='Get Available Crops',
    description='Returns list of all supported crops for yield predictions. Use this to populate crop dropdown in frontend.',
    responses={
        200: OpenApiResponse(
            description='List of crops',
            response={
                'type': 'object',
                'properties': {
                    'crops': {
                        'type': 'array',
                        'items': {
                            'type': 'object',
                            'properties': {
                                'value': {'type': 'string', 'example': 'maize'},
                                'label': {'type': 'string', 'example': 'Maize'}
                            }
                        }
                    },
                    'count': {'type': 'integer', 'example': 9}
                }
            }
        )
    }
)
@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def get_crops(request):
    """
    GET /api/v1/meta/crops/
    
    Returns all supported crops for predictions.
    Frontend should use this to populate crop dropdowns.
    
    Response format:
    {
        "crops": [
            {"value": "maize", "label": "Maize"},
            {"value": "beans", "label": "Beans"},
            ...
        ],
        "count": 9
    }
    """
    from .models import CROP_CHOICES
    
    crops_list = [
        {'value': value, 'label': label}
        for value, label in CROP_CHOICES
    ]
    
    return Response({
        'crops': crops_list,
        'count': len(crops_list)
    })

