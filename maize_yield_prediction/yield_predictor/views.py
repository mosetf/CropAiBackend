from django.shortcuts import render
import pandas as pd
import numpy as np
import pickle
import requests
from django.conf import settings
import os
import logging
from django.contrib.auth.decorators import login_required

logger = logging.getLogger('weather')

def get_weather_data(location="Eldoret"):
    location_coords = {
        "Nakuru": {"lat": -0.3031, "lon": 36.0800},
        "Eldoret": {"lat": 0.5143, "lon": 35.2698},
        "Kitale": {"lat": 1.0157, "lon": 35.0062},
        "Naivasha": {"lat": -0.7072, "lon": 36.4319},
        "Narok": {"lat": -1.0878, "lon": 35.8711},
        "Kericho": {"lat": -0.3689, "lon": 35.2831},
        "Kapsabet": {"lat": 0.2039, "lon": 35.1053},
        "Kabarnet": {"lat": 0.4919, "lon": 35.7434},
        "Iten": {"lat": 0.6703, "lon": 35.5081},
        "Nyahururu": {"lat": 0.0421, "lon": 36.3673},
        "Lake Nakuru": {"lat": -0.3031, "lon": 36.0800},
        "Lake Naivasha": {"lat": -0.7072, "lon": 36.4319},
        "Lake Baringo": {"lat": 0.6400, "lon": 36.0800},
        "Lake Bogoria": {"lat": 0.2500, "lon": 36.1000},
        "Lake Elementaita": {"lat": -0.4500, "lon": 36.2500},
        "Kerio Valley": {"lat": 0.6000, "lon": 35.6000},
        "Mau Escarpment": {"lat": -0.6000, "lon": 35.7500},
        "Tugen Hills": {"lat": 0.5000, "lon": 35.9000},
        "Cherangani Hills": {"lat": 1.1000, "lon": 35.4500},
        "Bomet": {"lat": -0.7813, "lon": 35.3416}
    }

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
        return None, used_fallback


def landing_page(request):
    return render(request, 'yield_predictor/landing.html')


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
        planting_date = int(request.POST.get('planting_date', 90))
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

        weather, fallback_used = get_weather_data(location)
        if not weather:
            return render(request, 'yield_predictor/predict_yield.html', {
                'locations': locations,
                'error': 'Weather data unavailable.'
            })

        input_data = {
            'Year': 2025,
            'Rainfall (mm)': weather['rainfall'],
            'Avg_Temperature (°C)': weather['temperature'],
            'Humidity (%)': weather['humidity'],
            'Soil_Moisture (%)': soil_moisture,
            'Soil_pH': soil_ph,
            'Organic_Carbon (%)': organic_carbon,
            'Fertilizer (kg/ha)': fertilizer,
            'Planting_Date': planting_date,
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
        best_days, best_profit = optimize_harvest(yield_pred, market_price, labour_cost, storage_loss)

        return render(request, 'yield_predictor/predict_yield.html', {
            'locations': locations,
            'yield_pred': round(yield_pred, 2),
            'best_days': best_days,
            'best_profit': round(best_profit, 2),
            'weather': weather,
            'fallback_used': fallback_used
        })

    return render(request, 'yield_predictor/predict_yield.html', {'locations': locations})


def optimize_harvest(yield_pred, market_price, labour_cost, storage_loss, days_range=range(90, 151)):
    profits = []
    for days in days_range:
        adjusted_loss = storage_loss + (days - 90) * 0.1
        adjusted_loss = min(adjusted_loss, 30)
        profit = (yield_pred * market_price * (1 - adjusted_loss / 100) - labour_cost)
        profits.append((days, profit))
    best_days, best_profit = max(profits, key=lambda x: x[1])
    return best_days, best_profit
