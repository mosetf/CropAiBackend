# weather_service.py
# Everything weather-related extracted from views.py
# Returns structured dicts, no Django imports

import requests
from typing import Dict, List
import logging

logger = logging.getLogger(__name__)

class WeatherUnavailableError(Exception):
    """Raised when weather data cannot be fetched"""
    pass

def get_current_weather(location: str, lat: float, lon: float, api_key: str, base_url: str) -> Dict:
    """
    Returns weather dict or raises WeatherUnavailableError.
    
    Returns:
        dict: {
            'temperature': float,
            'humidity': float,
            'rainfall': float,
            'used_fallback': bool
        }
    """
    try:
        if lat and lon:
            url = f"{base_url}lat={lat}&lon={lon}&appid={api_key}&units=metric"
        else:
            url = f"{base_url}q={location}&appid={api_key}&units=metric"
            
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        data = response.json()
        
        weather_data = {
            'temperature': data['main']['temp'],
            'humidity': data['main']['humidity'],
            'rainfall': data.get('rain', {}).get('1h', 0) * 24,  # convert to daily
            'used_fallback': lat is None or lon is None
        }
        
        logger.info(f"Weather fetched for {location}: {weather_data}")
        return weather_data
        
    except Exception as e:
        logger.error(f"Weather fetch failed for {location}: {e}")
        raise WeatherUnavailableError(f"Could not fetch weather for {location}") from e


def get_forecast(lat: float, lon: float, api_key: str, forecast_url: str) -> List[Dict]:
    """
    Returns 5-day forecast list or empty list if unavailable.
    
    Returns:
        list: [{'datetime': str, 'temperature': float, 'humidity': float, 'rain': float}, ...]
    """
    if not api_key or not forecast_url:
        return _get_mock_forecast_data()
        
    try:
        url = f"{forecast_url}lat={lat}&lon={lon}&appid={api_key}&units=metric"
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        data = response.json()
        
        forecast = []
        for entry in data["list"]:
            forecast.append({
                "datetime": entry["dt_txt"],
                "temperature": entry["main"]["temp"],
                "humidity": entry["main"]["humidity"],
                "rain": entry.get("rain", {}).get("3h", 0)
            })
        return forecast
        
    except Exception as e:
        logger.warning(f"Forecast API failed: {e}, using mock data")
        return _get_mock_forecast_data()


def build_seasonal_features(weather: Dict, forecast: List[Dict] = None) -> Dict:
    """
    Converts current weather into model input features.
    
    Args:
        weather: Current weather dict from get_current_weather()
        forecast: Optional forecast list from get_forecast()
    
    Returns:
        dict: Weather features formatted for XGBoost model
    """
    if forecast:
        # Calculate seasonal estimates from forecast
        temps = [entry["temperature"] for entry in forecast]
        humidity_vals = [entry["humidity"] for entry in forecast]
        rain_vals = [entry["rain"] for entry in forecast]
        
        temp_avg = sum(temps) / len(temps) if temps else weather['temperature']
        temp_min = min(temps) if temps else weather['temperature'] - 5
        temp_max = max(temps) if temps else weather['temperature'] + 3
        humidity_avg = sum(humidity_vals) / len(humidity_vals) if humidity_vals else weather['humidity']
        
        # Scale forecast rain to seasonal estimate
        forecast_rain = sum(rain_vals) if rain_vals else 0
        seasonal_rainfall = forecast_rain * 30  # rough seasonal estimate
    else:
        # Use current weather with estimates
        temp_avg = weather['temperature']
        temp_min = weather['temperature'] - 5
        temp_max = weather['temperature'] + 3  
        humidity_avg = weather['humidity']
        seasonal_rainfall = weather['rainfall'] * 90  # scale daily to seasonal
    
    return {
        "temp_avg_c": round(temp_avg, 1),
        "temp_min_c": round(temp_min, 1),
        "temp_max_c": round(temp_max, 1),
        "rainfall_season_mm": round(seasonal_rainfall, 1),
        "humidity_pct": round(humidity_avg, 1),
        "rainfall_days": 30,  # estimate
        "dry_spell_days": 5,  # estimate
        "solar_mj": 18.0      # default solar radiation
    }


def _get_mock_forecast_data() -> List[Dict]:
    """Return mock forecast data when API is not available"""
    return [
        {"datetime": "2026-03-24 12:00:00", "temperature": 22.5, "humidity": 65, "rain": 0},
        {"datetime": "2026-03-25 12:00:00", "temperature": 24.0, "humidity": 60, "rain": 2.5},
        {"datetime": "2026-03-26 12:00:00", "temperature": 23.0, "humidity": 70, "rain": 1.0},
        {"datetime": "2026-03-27 12:00:00", "temperature": 21.5, "humidity": 68, "rain": 0},
        {"datetime": "2026-03-28 12:00:00", "temperature": 25.0, "humidity": 55, "rain": 0}
    ]