from django.conf import settings
import requests


location_coords = { "Nakuru": { "lat": -0.3031,
"lon": 36.0800 },
"Eldoret": { "lat": 0.5143,
"lon": 35.2698 },
"Kitale": { "lat": 1.0157,
"lon": 35.0062 },
"Naivasha": { "lat": -0.7072,
"lon": 36.4319 },
"Narok": { "lat": -1.0878,
"lon": 35.8711 },
"Kericho": { "lat": -0.3689,
"lon": 35.2831 },
"Kapsabet": { "lat": 0.2039,
"lon": 35.1053 },
"Kabarnet": { "lat": 0.4919,
"lon": 35.7434 },
"Iten": { "lat": 0.6703,
"lon": 35.5081 },
"Nyahururu": { "lat": 0.0421,
"lon": 36.3673 },
"Lake Nakuru": { "lat": -0.3031,
"lon": 36.0800 },
"Lake Naivasha": { "lat": -0.7072,
"lon": 36.4319 },
"Lake Baringo": { "lat": 0.6400,
"lon": 36.0800 },
"Lake Bogoria": { "lat": 0.2500,
"lon": 36.1000 },
"Lake Elementaita": { "lat": -0.4500,
"lon": 36.2500 },
"Kerio Valley": { "lat": 0.6000,
"lon": 35.6000 },
"Mau Escarpment": { "lat": -0.6000,
"lon": 35.7500 },
"Tugen Hills": { "lat": 0.5000,
"lon": 35.9000 },
"Cherangani Hills": { "lat": 1.1000,
"lon": 35.4500 },
"Bomet": { "lat": -0.7813,
"lon": 35.3416 } }

def get_forecast_data(lat, lon):
    url = f"{settings.FORECAST_URL}lat={lat}&lon={lon}&appid={settings.API_KEY}&units=metric"
    try:
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
        print(f"Forecast API error: {e}")
        return []