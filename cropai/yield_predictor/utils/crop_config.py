from pathlib import Path
from django.conf import settings

BASE_DIR = settings.BASE_DIR
MODEL_DIR = settings.MODEL_DIR

AVAILABLE_CROPS = {
    'maize': {'model_file': 'maize_yield_model.pkl', 'label': 'Maize', 'available': True},
    'beans': {'model_file': 'beans_yield_model.pkl', 'label': 'Beans', 'available': True},
    'wheat': {'model_file': 'wheat_yield_model.pkl', 'label': 'Wheat', 'available': True},
    'sorghum': {'model_file': 'sorghum_yield_model.pkl', 'label': 'Sorghum', 'available': True},
    'coffee': {'model_file': 'coffee_yield_model.pkl', 'label': 'Coffee', 'available': True},
    'tea': {'model_file': 'tea_yield_model.pkl', 'label': 'Tea', 'available': True},
    'potatoes': {'model_file': 'potatoes_yield_model.pkl', 'label': 'Potatoes', 'available': True},
    'cassava': {'model_file': None, 'label': 'Cassava', 'available': False},
    'rice': {'model_file': None, 'label': 'Rice', 'available': False},
}

def get_available_crops():
    return {k: v for k, v in AVAILABLE_CROPS.items() if v['available']}

def get_all_crops():
    return AVAILABLE_CROPS

def is_crop_available(crop_name):
    return AVAILABLE_CROPS.get(crop_name, {}).get('available', False)

def get_crop_label(crop_name):
    return AVAILABLE_CROPS.get(crop_name, {}).get('label', crop_name.title())

def get_crop_model_path(crop_name):
    model_file = AVAILABLE_CROPS.get(crop_name, {}).get('model_file')
    if model_file:
        return MODEL_DIR / model_file
    return None

def get_available_crop_choices():
    available = get_available_crops()
    return [(code, config['label']) for code, config in available.items()]

def get_all_crop_choices():
    all_crops = get_all_crops()
    return [(code, config['label']) for code, config in all_crops.items()]
