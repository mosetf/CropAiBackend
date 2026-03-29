"""
yield_predictor/views.py - All views: function-based and DRF viewsets
"""
import json
from datetime import datetime

from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.conf import settings
from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from rest_framework.decorators import action

from .models import YieldPrediction, CropModel
from .serializers import PredictionInputForm, YieldPredictionSerializer, CropModelSerializer
from .services import prediction_service, weather_service
from .services.prediction_service import LOCATION_COORDS
from .utils.crop_config import is_crop_available, get_available_crop_choices, get_all_crop_choices

# FUNCTION-BASED VIEWS (Traditional Django views for HTML)

def landing_page(request):
    return render(request, 'yield_predictor/landing.html')


@login_required
def dashboard(request):
    predictions = YieldPrediction.objects.filter(
        user=request.user
    ).order_by('-created_at')[:50]

    forecast = []
    latest_location = predictions[0].location if predictions else 'Nakuru'
    coords = LOCATION_COORDS.get(latest_location, {'lat': -0.3031, 'lon': 36.08})
    try:
        forecast = weather_service.get_forecast(
            lat=coords['lat'],
            lon=coords['lon'],
            api_key=settings.API_KEY,
            forecast_url=settings.FORECAST_URL,
        )
    except Exception:
        pass

    chart_data = None
    if predictions:
        chart_data = {
            'labels':   [p.created_at.strftime('%b %d') for p in predictions[:10]],
            'yields':   [float(p.predicted_yield) for p in predictions[:10]],
            'profits':  [float(p.net_profit or 0) for p in predictions[:10]],
            'rainfall': [float(p.rainfall or 0) for p in predictions[:10]],
        }

    all_crops = get_all_crop_choices()
    available_crops = get_available_crop_choices()
    coming_soon = [c[0] for c in all_crops if c not in available_crops]

    return render(request, 'yield_predictor/dashboard.html', {
        'predictions':      predictions,
        'locations':        sorted(LOCATION_COORDS.keys()),
        'forecast':         forecast,
        'chart_data_json':  json.dumps(chart_data) if chart_data else None,
        'available_crops':  available_crops,
        'coming_soon_crops': coming_soon,
    })


@login_required
def predict_yield(request):
    if request.method == 'POST':
        form = PredictionInputForm(request.POST)
        
        crop = request.POST.get('crop', '')
        if crop and not is_crop_available(crop):
            form.add_error('crop', f'Model for {crop} is not yet available. Please select from available crops.')
            return render(request, 'yield_predictor/predict_yield.html', {
                'form':      form,
                'locations': sorted(LOCATION_COORDS.keys()),
                'available_crops': get_available_crop_choices(),
            })

        if not form.is_valid():
            return render(request, 'yield_predictor/predict_yield.html', {
                'form':      form,
                'locations': sorted(LOCATION_COORDS.keys()),
                'available_crops': get_available_crop_choices(),
            })

        service_input = form.to_service_dict()

        result = prediction_service.run_prediction(
            crop=service_input['crop'],
            location=service_input['location'],
            soil_data=service_input['soil_data'],
            fertilizer=service_input['fertilizer'],
            planting_date=service_input['planting_date'],
            api_settings={
                'api_key':      settings.API_KEY,
                'base_url':     settings.BASE_URL,
                'forecast_url': settings.FORECAST_URL,
            },
            market_price_override=service_input.get('market_price_override'),
            labour_cost_override=service_input.get('labour_cost_override'),
        )

        if not result['success']:
            form.add_error(None, result['error'])
            return render(request, 'yield_predictor/predict_yield.html', {
                'form':      form,
                'locations': sorted(LOCATION_COORDS.keys()),
                'available_crops': get_available_crop_choices(),
            })

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
            rainfall=result['weather_data']['rainfall'],
            temperature=result['weather_data']['temp'],
            humidity=result['weather_data']['humidity'],
            soil_ph=service_input['soil_data']['soil_ph'],
            soil_moisture=service_input['soil_data']['soil_moisture'],
            organic_carbon=service_input['soil_data']['organic_carbon'],
            fertilizer_kg_ha=service_input['fertilizer'],
            ai_recommendations=result['ai_recommendations'],
            risk_level=result['risk_level'],
            risk_reason=result['risk_reason'],
            fallback_used=result['fallback_used'],
            model_version=result.get('model_source', ''),
        )

        return render(request, 'yield_predictor/predict_yield.html', {
            'form':        PredictionInputForm(),
            'locations':   sorted(LOCATION_COORDS.keys()),
            'result':      result,
            'prediction':  prediction,
            'available_crops': get_available_crop_choices(),
        })

    return render(request, 'yield_predictor/predict_yield.html', {
        'form':      PredictionInputForm(),
        'locations': sorted(LOCATION_COORDS.keys()),
        'available_crops': get_available_crop_choices(),
    })


# DRF VIEWSETS (REST API endpoints)
class YieldPredictionViewSet(viewsets.ModelViewSet):
    """
    API endpoint for yield predictions.
    
    list:    GET /api/v1/predictions/
    create:  POST /api/v1/predictions/
    retrieve: GET /api/v1/predictions/{id}/
    destroy: DELETE /api/v1/predictions/{id}/
    """
    serializer_class = YieldPredictionSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return YieldPrediction.objects.filter(user=self.request.user)
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class CropModelViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint for crop models (read-only).
    
    list:    GET /api/v1/crops/
    retrieve: GET /api/v1/crops/{id}/
    """
    queryset = CropModel.objects.filter(is_active=True)
    serializer_class = CropModelSerializer
    permission_classes = [permissions.AllowAny]
