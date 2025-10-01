from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
import pandas as pd
import numpy as np
import pickle
import requests
from django.conf import settings
import os
import logging
from datetime import datetime, timedelta
import json
from .models import YieldPrediction
from .utils.weather_utils import get_forecast_data, location_coords

logger = logging.getLogger('weather')


def get_weather_data(location="Eldoret"):

    used_fallback = False

    try:
        if location in location_coords:
            lat = location_coords[location]['lat']
            lon = location_coords[location]['lon']
            url = f"{settings.BASE_URL}lat={lat}&lon={lon}&appid={settings.API_KEY}&units=metric"
        else:
            url = f"{settings.BASE_URL}q={location}&appid={settings.API_KEY}&units=metric"
            used_fallback = True

        response = requests.get(url, timeout=5)
        response.raise_for_status()
        data = response.json()

        weather_data = {
            'rainfall': data.get('rain', {}).get('1h', 0) * 24,  # approximate daily
            'temperature': data['main']['temp'],
            'humidity': data['main']['humidity']
        }

        logger.info(
            f"Weather fetched for {location}: "
            f"rainfall={weather_data['rainfall']}mm, "
            f"temp={weather_data['temperature']}°C, "
            f"humidity={weather_data['humidity']}%"
        )

        return weather_data, used_fallback

    except Exception as e:
        logger.error(f"Weather API error for {location}: {e}")
        weather_data = {
            'rainfall': 800,
            'temperature': 20,
            'humidity': 70
        }
        used_fallback = True
        logger.info(
            f"Using fallback weather data for {location}: "
            f"rainfall={weather_data['rainfall']}mm, "
            f"temp={weather_data['temperature']}°C, "
            f"humidity={weather_data['humidity']}%"
        )
        return weather_data, used_fallback

def landing_page(request):
    return render(request, 'yield_predictor/landing.html')

@login_required
def dashboard(request):
    predictions = YieldPrediction.objects.filter(user=request.user).order_by('-created_at')
    
    locations = [
        "Nakuru", "Eldoret", "Kitale", "Naivasha", "Narok", "Kericho", "Kapsabet",
        "Kabarnet", "Iten", "Nyahururu", "Lake Nakuru", "Lake Naivasha", "Lake Baringo",
        "Lake Bogoria", "Lake Elementaita", "Kerio Valley", "Mau Escarpment", "Tugen Hills",
        "Cherangani Hills", "Bomet"
    ]

    # Get the latest prediction's location or fallback to Eldoret
    latest_location = predictions[0].location if predictions else "Eldoret"
    coords = location_coords.get(latest_location, {"lat": 0.5143, "lon": 35.2698})

    # Fetch the forecast data
    forecast = get_forecast_data(lat=coords["lat"], lon=coords["lon"])

    chart_data = None
    if predictions:
        chart_data = {
            'labels': [p.created_at.strftime('%b %d') for p in predictions],
            'rainfall': [float(p.rainfall or 0) for p in predictions],
            'profit': [float(p.net_profit or 0) for p in predictions]
        }

    return render(request, 'yield_predictor/dashboard.html', {
        'predictions': predictions,
        'locations': locations,
        'forecast': forecast,
        'chart_data_json': json.dumps(chart_data) if chart_data else None
    })


@login_required
def predict_yield(request):
    locations = [
        "Nakuru", "Eldoret", "Kitale", "Naivasha", "Narok", "Kericho", "Kapsabet",
        "Kabarnet", "Iten", "Nyahururu", "Lake Nakuru", "Lake Naivasha", "Lake Baringo",
        "Lake Bogoria", "Lake Elementaita", "Kerio Valley", "Mau Escarpment", "Tugen Hills",
        "Cherangani Hills", "Bomet"
    ]

    if request.method == 'POST':
        location = request.POST.get('location', 'Eldoret')
        soil_moisture = float(request.POST.get('soil_moisture', 25))
        soil_ph = float(request.POST.get('soil_ph', 6.0))
        organic_carbon = float(request.POST.get('organic_carbon', 1.5))
        fertilizer = float(request.POST.get('fertilizer', 100))
        planting_date_str = request.POST.get('planting_date')
        try:
            planting_date = datetime.strptime(planting_date_str, "%Y-%m-%d")
            planting_day = planting_date.timetuple().tm_yday
        except (ValueError, TypeError):
            return render(request, 'yield_predictor/predict_yield.html', {
                'locations': locations,
                'error': 'Invalid planting date format.'
            })
        prev_yield = float(request.POST.get('prev_yield', 3.5))
        market_price = float(request.POST.get('market_price', 3500))
        labour_cost = float(request.POST.get('labour_cost', 1000))
        storage_loss = float(request.POST.get('storage_loss', 15))

        model_path = os.path.join(settings.BASE_DIR, 'models', 'rf_yield_model.pkl')
        try:
            with open(model_path, 'rb') as f:
                model = pickle.load(f)
        except FileNotFoundError:
            return render(request, 'yield_predictor/predict_yield.html', {
                'locations': locations,
                'error': 'Model file not found. Please contact admin.'
            })

        # Fetch weather data
        weather, fallback_used = get_weather_data(location)
        if not weather:
            return render(request, 'yield_predictor/predict_yield.html', {
                'locations': locations,
                'error': 'Weather data unavailable.'
            })

        # Prepare input data
        input_data = {
            'Year': 2025,
            'Rainfall (mm)': weather['rainfall'],
            'Avg_Temperature (°C)': weather['temperature'],
            'Humidity (%)': weather['humidity'],
            'Soil_Moisture (%)': soil_moisture,
            'Soil_pH': soil_ph,
            'Organic_Carbon (%)': organic_carbon,
            'Fertilizer (kg/ha)': fertilizer,
            'Planting_Date': planting_day,
            'Prev_Yield (tons/ha)': prev_yield
        }

        for loc in locations[1:]:
            input_data[f'Location_{loc}'] = 1 if loc == location else 0

        input_df = pd.DataFrame([input_data])

        try:
            model_columns = model.feature_names_in_
            input_df = input_df.reindex(columns=model_columns, fill_value=0)
        except AttributeError:
            return render(request, 'yield_predictor/predict_yield.html', {
                'locations': locations,
                'error': 'Model is not properly configured.'
            })

        yield_pred = model.predict(input_df)[0]
        harvest_window, best_profit = optimize_harvest(
            yield_pred, market_price, labour_cost, storage_loss, planting_date
        )

        YieldPrediction.objects.create(
            user=request.user,
            location=location,
            planting_date=planting_date,
            predicted_yield=round(yield_pred, 2),
            harvest_window=harvest_window,
            net_profit=round(best_profit, 2),
            rainfall=weather['rainfall'],
            temperature=weather['temperature'],
            humidity=weather['humidity'],
            fallback_used=fallback_used
        )

        return render(request, 'yield_predictor/predict_yield.html', {
            'locations': locations,
            'yield_pred': round(yield_pred, 2),
            'best_days': harvest_window,
            'best_profit': round(best_profit, 2),
            'weather': weather,
            'fallback_used': fallback_used
        })

    return render(request, 'yield_predictor/predict_yield.html', {'locations': locations})


def optimize_harvest(yield_pred, market_price, labour_cost, storage_loss, planting_date, days_range=range(90, 151)):
    profits = []
    for days in days_range:
        adjusted_loss = storage_loss + (days - 90) * 0.1
        adjusted_loss = min(adjusted_loss, 30)
        profit = (yield_pred * market_price * (1 - adjusted_loss / 100) - labour_cost)
        harvest_date = planting_date + timedelta(days=days)
        profits.append((harvest_date, profit))

    # Find the best harvest date by max profit
    best_date, best_profit = max(profits, key=lambda x: x[1])

    # Define a window of ±7 days for flexibility
    start_date = (best_date - timedelta(days=3)).strftime("%d %B %Y")
    end_date = (best_date + timedelta(days=3)).strftime("%d %B %Y")
    harvest_window = f"{start_date} to {end_date}"
    return harvest_window, best_profit