import json
import logging
from datetime import datetime

from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.conf import settings

from .models import YieldPrediction
from .serializers import PredictionInputForm
from .services import prediction_service, weather_service
from .services.prediction_service import LOCATION_COORDS

logger = logging.getLogger(__name__)


# ─── public ────────────────────────────────────────────────────────────────────

def landing_page(request):
    return render(request, 'yield_predictor/landing.html')


# ─── dashboard ─────────────────────────────────────────────────────────────────

@login_required
def dashboard(request):
    predictions = YieldPrediction.objects.filter(
        user=request.user
    ).order_by('-created_at')[:50]

    # Weather forecast for the user's most recent prediction location
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
    except Exception as e:
        logger.warning(f'Dashboard forecast failed: {e}')

    # Chart data for the last 10 predictions
    chart_data = None
    if predictions:
        chart_data = {
            'labels':   [p.created_at.strftime('%b %d') for p in predictions[:10]],
            'yields':   [float(p.predicted_yield) for p in predictions[:10]],
            'profits':  [float(p.net_profit or 0) for p in predictions[:10]],
            'rainfall': [float(p.rainfall or 0) for p in predictions[:10]],
        }

    return render(request, 'yield_predictor/dashboard.html', {
        'predictions':      predictions,
        'locations':        sorted(LOCATION_COORDS.keys()),
        'forecast':         forecast,
        'chart_data_json':  json.dumps(chart_data) if chart_data else None,
    })


# ─── prediction ────────────────────────────────────────────────────────────────

@login_required
def predict_yield(request):
    """
    GET  — render blank prediction form
    POST — validate → run prediction service → save → render result
    """

    if request.method == 'POST':
        form = PredictionInputForm(request.POST)

        if not form.is_valid():
            # Return the form with validation errors highlighted
            return render(request, 'yield_predictor/predict_yield.html', {
                'form':      form,
                'locations': sorted(LOCATION_COORDS.keys()),
            })

        # Form is valid — run the full prediction pipeline
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
        )

        if not result['success']:
            form.add_error(None, result['error'])
            return render(request, 'yield_predictor/predict_yield.html', {
                'form':      form,
                'locations': sorted(LOCATION_COORDS.keys()),
            })

        # Save prediction to database
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
            'form':        PredictionInputForm(),   # fresh form for next prediction
            'locations':   sorted(LOCATION_COORDS.keys()),
            'result':      result,
            'prediction':  prediction,
        })

    # GET request — blank form
    return render(request, 'yield_predictor/predict_yield.html', {
        'form':      PredictionInputForm(),
        'locations': sorted(LOCATION_COORDS.keys()),
    })