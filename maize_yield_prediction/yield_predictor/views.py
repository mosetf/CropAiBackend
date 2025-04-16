from django.views.decorators.csrf import csrf_exempt
import os
import joblib
import pandas as pd
from django.http import JsonResponse
from src import optimization
from django.shortcuts import render

# Get absolute path to the Django app directory
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL_PATH = os.path.join(BASE_DIR, 'yield_predictor', 'maize_yield_kenya_model.pkl')


# Load the trained Random Forest model from the correct location
if os.path.exists(MODEL_PATH):
    model = joblib.load(MODEL_PATH)
else:
    model = None  # Model is missing

def landing_page(request):
    return render(request, 'yield_predictor/landing.html')    

@csrf_exempt
def predict_yield(request):
    if request.method == 'POST':
        # Ensure the model is loaded
        if model is None:
            return JsonResponse({"error": "Model not found. Ensure the model file exists at 'yield_predictor/maize_yield_kenya_model.pkl'."}, status=500)

        try:
            # Get input values from request
            rainfall = float(request.POST.get('rainfall'))
            temperature = float(request.POST.get('temperature'))
            soil_pH = float(request.POST.get('soil_pH'))
            pesticides = float(request.POST.get('pesticides'))  # Add missing feature

            # Create DataFrame with the correct feature names
            input_data = pd.DataFrame([[rainfall, pesticides, temperature, soil_pH]],
                                      columns=['average_rain_fall_mm_per_year', 'pesticides_tonnes', 'avg_temp', 'rainfall_to_temp_ratio'])

            # Make prediction
            prediction = model.predict(input_data)[0]

            return JsonResponse({"predicted_yield": prediction})

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)

    return JsonResponse({"message": "Use POST method to submit data."})

def optimization_view(request):
    # Load data
    df = optimization.load_processed_data()

    # Run optimization
    harvest = optimization.recommend_harvest_schedule(df.copy(), rain_prob=0.3, temperature=26)
    market = optimization.optimize_market_sales(df.copy())
    pesticide = optimization.pesticide_recommendation(df.copy(), rain_forecast=0.7)

    # Combine results
    result_df = df.copy()
    result_df['Harvest_Decision'] = harvest['Harvest_Decision']
    result_df['Sell_Now'] = market['Sell_Now']
    result_df['Reduce_Pesticide'] = pesticide['Reduce_Pesticide']

    # Pass to template as dict
    context = {
        'results': result_df[['Year', 'Harvest_Decision', 'Sell_Now', 'Reduce_Pesticide']].head(20).to_dict('records')  # Limit for testing
    }

    return render(request, 'optimization_results.html', context)
