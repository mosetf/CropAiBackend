"""
yield_predictor/views.py - DRF viewsets and API endpoints only
"""
from django.conf import settings
from rest_framework import viewsets, mixins, permissions, status
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from drf_spectacular.utils import extend_schema, OpenApiResponse

from .models import YieldPrediction, CropModel
from .serializers import YieldPredictionSerializer, CropModelSerializer, PredictionInputForm
from .services.prediction_service import LOCATION_COORDS, run_prediction
from .services.weather_service import get_current_weather as fetch_weather, WeatherUnavailableError

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
    API endpoint for yield predictions.

    list:    GET /api/v1/predictions/
             Returns paginated list of user's predictions

    create:  POST /api/v1/predictions/
             Create new prediction — runs XGBoost + RAG pipeline

    retrieve: GET /api/v1/predictions/{id}/
              Get specific prediction by ID

    destroy: DELETE /api/v1/predictions/{id}/
             Delete a prediction

    Input fields (POST):
    - crop: str (maize, wheat, beans, etc)
    - location: str (Nakuru, Mombasa, etc)
    - soil_ph: float (3–10)
    - soil_moisture: float (0–100%)
    - organic_carbon: float (0–20%)
    - fertilizer_kg_ha: float (kg/ha)
    - planting_date: date (YYYY-MM-DD)
    - rainfall: float (mm/season)
    - temperature: float (°C average)
    - humidity: float (% relative)
    - market_price: float (optional, KES/tonne override)
    - labour_cost: float (optional, KES/ha override)

    Computed by backend (do NOT send):
    - predicted_yield, yield_low, yield_high
    - harvest_window, net_profit
    - ai_recommendations, risk_level, risk_reason
    """
    serializer_class = YieldPredictionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return YieldPrediction.objects.filter(user=self.request.user)

    def create(self, request, *args, **kwargs):
        # Map frontend field names to form field names
        form_data = dict(request.data)
        if 'fertilizer_kg_ha' in form_data:
            form_data['fertilizer'] = form_data.pop('fertilizer_kg_ha')

        # Validate input using PredictionInputForm
        form = PredictionInputForm(form_data)
        if not form.is_valid():
            return Response(form.errors, status=status.HTTP_400_BAD_REQUEST)

        # Run the full prediction pipeline
        service_input = form.to_service_dict()
        result = run_prediction(
            crop=service_input['crop'],
            location=service_input['location'],
            soil_data=service_input['soil_data'],
            fertilizer=service_input['fertilizer'],
            planting_date=service_input['planting_date'],
            api_settings={
                'api_key': settings.API_KEY,
                'base_url': settings.BASE_URL,
                'forecast_url': settings.FORECAST_URL,
            },
            market_price_override=service_input.get('market_price_override'),
            labour_cost_override=service_input.get('labour_cost_override'),
        )

        if not result['success']:
            return Response(
                {'detail': result.get('error', 'Prediction failed')},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        # Override weather with user-provided values if present
        user_rainfall = request.data.get('rainfall', result['weather_data']['rainfall'])
        user_temp = request.data.get('temperature', result['weather_data']['temp'])
        user_humidity = request.data.get('humidity', result['weather_data']['humidity'])

        # Save to database
        prediction = YieldPrediction.objects.create(
            user=request.user,
            crop=service_input['crop'],
            location=service_input['location'],
            region=LOCATION_COORDS.get(service_input['location'], {}).get('region', ''),
            planting_date=service_input['planting_date'],
            season=result.get('season', ''),
            predicted_yield=result['predicted_yield'],
            yield_low=result['yield_range'][0],
            yield_high=result['yield_range'][1],
            harvest_window=result['harvest_window'],
            net_profit=result['net_profit'],
            rainfall=user_rainfall,
            temperature=user_temp,
            humidity=user_humidity,
            soil_ph=service_input['soil_data']['soil_ph'],
            soil_moisture=service_input['soil_data']['soil_moisture'],
            organic_carbon=service_input['soil_data']['organic_carbon'],
            fertilizer_kg_ha=service_input['fertilizer'],
            ai_recommendations=result['ai_recommendations'],
            risk_level=result['risk_level'],
            risk_reason=result.get('risk_reason', ''),
            fallback_used=result.get('fallback_used', False),
            model_version=result.get('model_source', ''),
        )

        serializer = self.get_serializer(prediction)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


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


@extend_schema(
    tags=['Weather'],
    summary='Get Current Weather',
    description='Returns current weather for a location using lat/lon. Used for live weather preview on the prediction form.',
    responses={
        200: OpenApiResponse(
            description='Current weather data',
            response={
                'type': 'object',
                'properties': {
                    'temperature': {'type': 'number', 'description': 'Temperature in °C'},
                    'humidity': {'type': 'number', 'description': 'Relative humidity %'},
                    'description': {'type': 'string', 'description': 'Weather description'},
                    'source': {'type': 'string', 'description': 'openweather or fallback'},
                }
            }
        )
    }
)
@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def get_current_weather(request):
    """
    GET /api/v1/weather/current/?lat=X&lon=Y

    Returns current weather for preview on the frontend.
    Does NOT require authentication.
    """
    lat = request.query_params.get('lat')
    lon = request.query_params.get('lon')

    if not lat or not lon:
        return Response(
            {'error': 'lat and lon query parameters are required'},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        lat_f = float(lat)
        lon_f = float(lon)
    except ValueError:
        return Response(
            {'error': 'lat and lon must be valid numbers'},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        weather = fetch_weather(
            location='',
            lat=lat_f,
            lon=lon_f,
            api_key=settings.API_KEY,
            base_url=settings.BASE_URL,
        )
        return Response({
            'temperature': round(weather['temperature'], 1),
            'humidity': round(weather['humidity'], 1),
            'description': 'Current conditions',
            'source': 'openweather',
        })
    except WeatherUnavailableError:
        return Response(
            {'error': f'Weather data unavailable for this location. Prediction will use estimated conditions.'},
            status=status.HTTP_503_SERVICE_UNAVAILABLE
        )
    except Exception:
        return Response(
            {'error': 'Unable to fetch weather data at this time.'},
            status=status.HTTP_502_BAD_GATEWAY
        )
