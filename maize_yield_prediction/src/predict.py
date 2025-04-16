from django.views.decorators.csrf import csrf_exempt
import os
import joblib
import pandas as pd
import requests
from django.http import JsonResponse
from dotenv import load_dotenv
from optimization import run_optimization

load_dotenv()

# Get absolute path to the Django app directory
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL_PATH = os.path.join(BASE_DIR, 'yield_predictor', 'maize_yield_kenya_model.pkl')

API_KEY = os.getenv("API_KEY")
BASE_URL = os.getenv("BASE_URL") 

# Load the trained Random Forest model from the correct location
if os.path.exists(MODEL_PATH):
    model = joblib.load(MODEL_PATH)
else:
    model = None

def get_weather_data(city="Eldoret"):
    """Fetch real-time weather data from OpenWeather API."""
    try:
        url = f"{BASE_URL}?q={city}&appid={API_KEY}&units=metric"
        response = requests.get(url)
        data = response.json()
        
        # Extract relevant weather data
        temperature = data["main"]["temp"]
        humidity = data["main"]["humidity"]

        return temperature, humidity
        
    except Exception as e:
        print(f"Error fetching weather data: {str(e)}")
        return None, None

@csrf_exempt
def predict_yield(request):
    if request.method == 'POST':
        if model is None:
            return JsonResponse({"error": "Model not found. Ensure the model file exists at 'yield_predictor/maize_yield_kenya_model.pkl'."}, status=500)
        try:
            city = request.POST.get('city', 'Eldoret')
            soil_pH = float(request.POST.get('soil_pH'))
            pesticides = float(request.POST.get('pesticides'))

            # Fetch real-time weather data
            temperature, humidity = get_weather_data(city)
            if temperature is None or humidity is None:
                return JsonResponse({"error": "Failed to fetch weather data."}, status=500)

            # Create DataFrame with correct feature names
            input_data = pd.DataFrame([[humidity, pesticides, temperature, soil_pH]],
                                      columns=['average_rain_fall_mm_per_year', 'pesticides_tonnes', 'avg_temp', 'rainfall_to_temp_ratio'])
            
            # Make prediction
            prediction = model.predict(input_data)[0]

            # Run optimization model
            yield_file = "data/processed/yield_df.xls"
            market_file = "data/processed/market_prices.xls"
            optimization_results = run_optimization(yield_file, market_file, city, pesticides)

            return JsonResponse({
                "city": city,
                "temperature (°C)": temperature,
                "humidity (%)": humidity,
                "predicted_yield (tons/ha)": prediction,
                "optimization": optimization_results
            })
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)
    return JsonResponse({"message": "Use POST method to submit data."})
