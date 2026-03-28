import json
from datetime import datetime

from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.conf import settings

from .models import YieldPrediction
from .serializers import PredictionInputForm
from .services import prediction_service, weather_service
from .services.prediction_service import LOCATION_COORDS


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

    return render(request, 'yield_predictor/dashboard.html', {
        'predictions':      predictions,
        'locations':        sorted(LOCATION_COORDS.keys()),
        'forecast':         forecast,
        'chart_data_json':  json.dumps(chart_data) if chart_data else None,
    })


@login_required
def predict_yield(request):
    if request.method == 'POST':
        form = PredictionInputForm(request.POST)

        if not form.is_valid():
            return render(request, 'yield_predictor/predict_yield.html', {
                'form':      form,
                'locations': sorted(LOCATION_COORDS.keys()),
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
        )

        if not result['success']:
            form.add_error(None, result['error'])
            return render(request, 'yield_predictor/predict_yield.html', {
                'form':      form,
                'locations': sorted(LOCATION_COORDS.keys()),
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
        })

    return render(request, 'yield_predictor/predict_yield.html', {
        'form':      PredictionInputForm(),
        'locations': sorted(LOCATION_COORDS.keys()),
    })