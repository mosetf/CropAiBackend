import pandas as pd
import os

# Get the base directory of the entire project (CropYieldPrediction)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def load_processed_data():
    # Correct file path pointing outside the Django app
    file_path = os.path.join('data', 'processed', 'maize_yield_dataset_500_enhanced.csv')
    
    # Load the data from CSV file
    try:
        return pd.read_csv(file_path)
    except FileNotFoundError:
        raise Exception(f"Data file not found at: {file_path}. Please make sure the dataset exists.")

def recommend_harvest_schedule(df, rain_prob=0.3, temperature=26):
    decisions = []
    for _, row in df.iterrows():
        if rain_prob > 0.6 or temperature > 30:
            decisions.append("Delay Harvest")
        else:
            decisions.append("Harvest Now")
    df['Harvest_Decision'] = decisions
    return df[['Year', 'Rainfall (mm)', 'Avg_Temperature (°C)', 'Harvest_Decision']]

def optimize_market_sales(df):
    threshold = df['Market_Price (KES/ton)'].quantile(0.75)
    df['Sell_Now'] = df['Market_Price (KES/ton)'] >= threshold
    return df[['Year', 'Market_Price (KES/ton)', 'Sell_Now']]

def pesticide_recommendation(df, rain_forecast=0.7):
    df['Reduce_Pesticide'] = rain_forecast > 0.6
    return df[['Year', 'Reduce_Pesticide']]
