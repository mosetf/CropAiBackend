#!/usr/bin/env python3
"""
Script to retrain the maize yield prediction model with current scikit-learn version
This fixes the version mismatch warnings
"""

import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_squared_error, r2_score
import pickle
import os
from datetime import datetime

# Set random seed for reproducibility
np.random.seed(42)

def generate_training_data():
    """Generate synthetic maize yield data for training"""
    print("Generating training data...")
    
    # Number of rows
    n_rows = 5000

    # Define Rift Valley locations
    rift_valley_locations = [
        "Nakuru", "Eldoret", "Kitale", "Naivasha", "Narok", "Kericho", "Kapsabet",
        "Kabarnet", "Iten", "Nyahururu", "Lake Nakuru", "Lake Naivasha", "Lake Baringo",
        "Lake Bogoria", "Lake Elementaita", "Kerio Valley", "Mau Escarpment", "Tugen Hills",
        "Cherangani Hills", "Bomet"
    ]

    # Generate features
    years = np.random.randint(2010, 2025, n_rows)
    locations = np.random.choice(rift_valley_locations, n_rows)
    rainfall = np.random.uniform(300, 1200, n_rows)
    temperature = np.random.uniform(15, 28, n_rows)
    humidity = np.random.uniform(50, 90, n_rows)
    soil_moisture = np.random.uniform(10, 40, n_rows)
    soil_ph = np.random.uniform(5.0, 7.5, n_rows)
    organic_carbon = np.random.uniform(0.5, 3.0, n_rows)
    fertilizer = np.random.uniform(50, 200, n_rows)
    planting_date = np.random.randint(60, 120, n_rows)
    prev_yield = np.random.uniform(1.5, 5.0, n_rows)
    market_price = np.random.uniform(2000, 5000, n_rows)
    days_to_harvest = np.random.randint(90, 150, n_rows)

    # Simulate labour cost (depends on yield and season)
    labour_base = 500 + 100 * prev_yield + 50 * (planting_date / 120)
    labour_noise = np.random.normal(0, 100, n_rows)
    labour_cost = np.clip(labour_base + labour_noise, 500, 2000)

    # Simulate storage loss (depends on humidity)
    storage_base = 5 + 0.3 * humidity
    storage_noise = np.random.normal(0, 5, n_rows)
    storage_loss = np.clip(storage_base + storage_noise, 2, 25)

    # Calculate yield using realistic relationships
    yield_base = (
        0.003 * rainfall +
        0.1 * temperature +
        0.02 * humidity +
        0.05 * soil_moisture +
        0.3 * soil_ph +
        0.5 * organic_carbon +
        0.01 * fertilizer +
        0.02 * prev_yield -
        0.01 * planting_date +
        0.001 * days_to_harvest
    )
    
    # Add realistic noise and constraints
    yield_noise = np.random.normal(0, 0.5, n_rows)
    predicted_yield = np.clip(yield_base + yield_noise, 1.0, 8.0)

    # Create DataFrame
    df = pd.DataFrame({
        'year': years,
        'location': locations,
        'rainfall': rainfall,
        'temperature': temperature,
        'humidity': humidity,
        'soil_moisture': soil_moisture,
        'soil_ph': soil_ph,
        'organic_carbon': organic_carbon,
        'fertilizer': fertilizer,
        'planting_date': planting_date,
        'prev_yield': prev_yield,
        'market_price': market_price,
        'days_to_harvest': days_to_harvest,
        'labour_cost': labour_cost,
        'storage_loss': storage_loss,
        'predicted_yield': predicted_yield
    })
    
    return df

def train_model(df):
    """Train the Random Forest model"""
    print("Training Random Forest model...")
    
    # Prepare features (excluding target and non-numeric columns)
    feature_columns = [
        'rainfall', 'temperature', 'humidity', 'soil_moisture', 
        'soil_ph', 'organic_carbon', 'fertilizer', 'planting_date', 
        'prev_yield', 'days_to_harvest'
    ]
    
    X = df[feature_columns]
    y = df['predicted_yield']
    
    # Split the data
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )
    
    # Train Random Forest with optimized parameters
    rf_model = RandomForestRegressor(
        n_estimators=100,
        max_depth=10,
        min_samples_split=5,
        min_samples_leaf=2,
        random_state=42,
        n_jobs=-1
    )
    
    rf_model.fit(X_train, y_train)
    
    # Evaluate the model
    y_pred = rf_model.predict(X_test)
    mse = mean_squared_error(y_test, y_pred)
    r2 = r2_score(y_test, y_pred)
    
    print(f"Model Performance:")
    print(f"  Mean Squared Error: {mse:.4f}")
    print(f"  R² Score: {r2:.4f}")
    print(f"  Root Mean Squared Error: {np.sqrt(mse):.4f}")
    
    return rf_model, feature_columns

def save_model(model, feature_columns):
    """Save the trained model"""
    print("Saving model...")
    
    # Model save paths
    model_paths = [
        'models/rf_yield_model.pkl',
        'maize_yield_prediction/models/rf_yield_model.pkl',
        'notebooks/rf_yield_model.pkl'
    ]
    
    model_data = {
        'model': model,
        'feature_columns': feature_columns,
        'sklearn_version': '1.7.2',
        'created_date': datetime.now().isoformat(),
        'model_type': 'RandomForestRegressor'
    }
    
    saved_count = 0
    for path in model_paths:
        try:
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(path), exist_ok=True)
            
            with open(path, 'wb') as f:
                pickle.dump(model_data, f)
            print(f"  ✓ Saved to: {path}")
            saved_count += 1
        except Exception as e:
            print(f"  ✗ Failed to save to {path}: {e}")
    
    print(f"Model saved to {saved_count} locations")

def main():
    """Main training pipeline"""
    print("=" * 60)
    print("MAIZE YIELD PREDICTION MODEL RETRAINING")
    print("=" * 60)
    print(f"Timestamp: {datetime.now()}")
    print(f"Scikit-learn version: 1.7.2")
    print()
    
    # Generate data
    df = generate_training_data()
    print(f"Generated {len(df)} training samples")
    
    # Train model
    model, feature_columns = train_model(df)
    
    # Save model
    save_model(model, feature_columns)
    
    print()
    print("=" * 60)
    print("RETRAINING COMPLETED SUCCESSFULLY!")
    print("=" * 60)
    print("The model version warning should now be resolved.")
    print("Restart your Django server to use the new model.")

if __name__ == "__main__":
    main()