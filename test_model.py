#!/usr/bin/env python3
"""
Test script to verify the model loads without warnings
"""

import pickle
import warnings
import numpy as np

def test_model_loading():
    """Test if the model loads without version warnings"""
    print("Testing model loading...")
    
    # Capture warnings
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        
        try:
            # Load the model
            with open('models/rf_yield_model.pkl', 'rb') as f:
                model_data = pickle.load(f)
            
            model = model_data['model']
            feature_columns = model_data['feature_columns']
            
            print("✓ Model loaded successfully!")
            print(f"✓ Model type: {type(model).__name__}")
            print(f"✓ Features: {len(feature_columns)} features")
            print(f"✓ Scikit-learn version used: {model_data.get('sklearn_version', 'Unknown')}")
            
            # Test prediction with dummy data
            test_data = np.random.rand(1, len(feature_columns))
            prediction = model.predict(test_data)
            print(f"✓ Test prediction: {prediction[0]:.2f} tons/ha")
            
            # Check for warnings
            sklearn_warnings = [warning for warning in w if 'sklearn' in str(warning.message).lower()]
            
            if sklearn_warnings:
                print(f"\n⚠️  Found {len(sklearn_warnings)} scikit-learn warnings:")
                for warning in sklearn_warnings:
                    print(f"   - {warning.message}")
            else:
                print("\n✅ No scikit-learn warnings found!")
                
        except Exception as e:
            print(f"✗ Error loading model: {e}")

if __name__ == "__main__":
    test_model_loading()