import joblib
import logging
from typing import Any
from pathlib import Path
from django.conf import settings

logger = logging.getLogger(__name__)

# Global model registry
_registry: dict = {}
_season_encoder = None

CROP_CHOICES = ["maize", "beans", "wheat", "sorghum", "coffee", "tea", "potatoes", "cassava", "rice"]


def get_model(crop: str) -> Any:
    """
    Load and cache XGBoost model for the specified crop.
    
    Args:
        crop: Crop name (e.g., 'maize', 'beans')
        
    Returns:
        Loaded XGBoost model object
        
    Raises:
        FileNotFoundError: If model file doesn't exist
        ValueError: If crop is not supported
    """
    if crop not in CROP_CHOICES:
        raise ValueError(f"Unsupported crop: {crop}. Available: {CROP_CHOICES}")
    
    if crop not in _registry:
        model_path = Path(settings.MODEL_DIR) / f'{crop}_yield_model.pkl'
        
        if not model_path.exists():
            raise FileNotFoundError(f"No model found for {crop} at {model_path}")
        
        try:
            logger.info(f"Loading XGBoost model for {crop} from {model_path}")
            _registry[crop] = joblib.load(model_path)
            logger.info(f"Successfully loaded {crop} model")
            
        except Exception as e:
            logger.error(f"Failed to load {crop} model: {e}")
            raise
    
    return _registry[crop]


def get_season_encoder() -> Any:
    """
    Load and cache the season encoder (transforms season names to numeric).
    
    Returns:
        Loaded LabelEncoder or similar encoder object
        
    Raises:
        FileNotFoundError: If encoder file doesn't exist
    """
    global _season_encoder
    
    if _season_encoder is None:
        encoder_path = Path(settings.MODEL_DIR) / "season_encoder.pkl"
        
        if not encoder_path.exists():
            raise FileNotFoundError(f"Season encoder not found at {encoder_path}")
        
        try:
            logger.info(f"Loading season encoder from {encoder_path}")
            _season_encoder = joblib.load(encoder_path)
            logger.info("Successfully loaded season encoder")
            
        except Exception as e:
            logger.error(f"Failed to load season encoder: {e}")
            raise
    
    return _season_encoder


def get_available_crops() -> list:
    """
    Get list of crops that have trained models available.
    
    Returns:
        List of crop names that have model files
    """
    available = []
    model_dir = Path(settings.MODEL_DIR)
    
    for crop in CROP_CHOICES:
        model_path = model_dir / f'{crop}_yield_model.pkl'
        if model_path.exists():
            available.append(crop)
    
    return available


def clear_model_cache():
    """
    Clear the model cache - useful for testing or reloading models.
    """
    global _registry, _season_encoder
    _registry.clear()
    _season_encoder = None
    logger.info("Model cache cleared")


def get_model_info(crop: str) -> dict:
    """
    Get metadata about a model without loading it.
    
    Args:
        crop: Crop name
        
    Returns:
        Dict with model metadata: {'path': str, 'exists': bool, 'size_mb': float}
    """
    model_path = Path(settings.MODEL_DIR) / f'{crop}_yield_model.pkl'
    
    info = {
        'path': str(model_path),
        'exists': model_path.exists(),
        'crop': crop,
    }
    
    if model_path.exists():
        try:
            size_bytes = model_path.stat().st_size
            info['size_mb'] = round(size_bytes / (1024 * 1024), 2)
        except Exception:
            info['size_mb'] = None
    else:
        info['size_mb'] = None
    
    return info


def validate_models() -> dict:
    """
    Validate all model files and return status report.
    
    Returns:
        Dict with validation results:
        {
            'valid_crops': list,
            'missing_crops': list, 
            'season_encoder_ok': bool,
            'total_models': int
        }
    """
    valid_crops = []
    missing_crops = []
    
    # Check crop models
    for crop in CROP_CHOICES:
        try:
            # Try to load model (this validates it)
            model = get_model(crop)
            valid_crops.append(crop)
        except (FileNotFoundError, ValueError):
            missing_crops.append(crop)
        except Exception as e:
            logger.warning(f"Model {crop} exists but failed to load: {e}")
            missing_crops.append(crop)
    
    # Check season encoder
    try:
        get_season_encoder()
        season_encoder_ok = True
    except Exception:
        season_encoder_ok = False
    
    return {
        'valid_crops': valid_crops,
        'missing_crops': missing_crops,
        'season_encoder_ok': season_encoder_ok,
        'total_models': len(valid_crops)
    }