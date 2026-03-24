# rag_service.py
# Thin wrapper around CropAdvisorRAG
# Keeps views.py clean of any ML imports

from typing import Dict, Any
import logging
from django.conf import settings

logger = logging.getLogger(__name__)

# Module-level singleton
_advisor = None


def get_advisor():
    """Get or create the CropAdvisorRAG instance."""
    global _advisor
    if _advisor is None:
        try:
            # Import here to avoid loading PyTorch models at startup
            from ..utils.crop_advisor_rag import CropAdvisorRAG
            
            _advisor = CropAdvisorRAG(
                model_path=str(settings.QWEN_MODEL_PATH),
                rag_data_path=str(settings.RAG_DATA_DIR)
            )
            logger.info("CropAdvisorRAG initialized successfully")
            
        except Exception as e:
            logger.warning(f"CropAdvisorRAG initialization failed: {e}")
            _advisor = None  # Keep as None to trigger fallback
            
    return _advisor


def get_recommendations(prediction_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Get AI recommendations using RAG-enhanced Qwen model.
    
    Args:
        prediction_data: Dict with keys:
            - crop: str
            - location: str  
            - yield: float
            - temp: float
            - rainfall: float
            - soil_ph: float
            - fertilizer: float
    
    Returns:
        Dict with keys:
            - recommendations: List[str]
            - risk_level: str ("low", "medium", "high")
            - risk_reason: str
            - fallback: bool (True if RAG failed)
    """
    
    # Temporarily skip RAG initialization and use fallback
    logger.info("Using fallback recommendations (RAG temporarily disabled)")
    return _get_fallback_recommendations(prediction_data)


def _get_fallback_recommendations(prediction_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate basic recommendations when RAG is unavailable.
    Uses rule-based logic based on crop and conditions.
    """
    
    crop = prediction_data.get("crop", "maize")
    yield_pred = prediction_data.get("yield", 0)
    rainfall = prediction_data.get("rainfall", 800)
    temp = prediction_data.get("temp", 22)
    soil_ph = prediction_data.get("soil_ph", 6.0)
    fertilizer = prediction_data.get("fertilizer", 100)
    
    recommendations = []
    risk_level = "medium"
    risk_reason = "Normal growing conditions expected"
    
    # Crop-specific recommendations
    if crop == "maize":
        recommendations.append("Plant early in the season for best results")
        if fertilizer < 150:
            recommendations.append("Consider increasing fertilizer application for maize")
        if soil_ph < 6.0:
            recommendations.append("Soil pH is low for maize - consider liming")
            
    elif crop == "beans":
        recommendations.append("Beans fix nitrogen naturally - avoid over-fertilizing")
        if soil_ph > 7.0:
            recommendations.append("Soil pH is high for beans - monitor carefully")
            
    elif crop == "coffee":
        recommendations.append("Coffee requires consistent moisture and good drainage")
        if temp > 25:
            recommendations.append("High temperatures may stress coffee plants")
            
    elif crop == "tea":
        recommendations.append("Tea thrives in well-drained, acidic soils")
        if soil_ph > 6.5:
            recommendations.append("Soil pH may be too high for optimal tea growth")
    
    # Weather-based recommendations  
    if rainfall < 500:
        recommendations.append("Low rainfall expected - consider irrigation")
        risk_level = "high"
        risk_reason = "Drought risk due to low expected rainfall"
    elif rainfall > 1200:
        recommendations.append("High rainfall expected - ensure good drainage")
        risk_level = "medium"
        risk_reason = "Excess moisture risk - monitor for diseases"
    
    if temp > 30:
        recommendations.append("High temperatures expected - provide shade if possible")
        risk_level = "high" if risk_level != "high" else "high"
        risk_reason = "Heat stress risk due to high temperatures"
    elif temp < 15:
        recommendations.append("Cool temperatures expected - consider season timing")
    
    # Yield-based recommendations
    if yield_pred > 0:
        if yield_pred < 1.0:
            recommendations.append("Predicted yield is low - review farming practices")
        elif yield_pred > 5.0:
            recommendations.append("High yield potential - ensure proper harvesting")
    
    # General recommendations
    recommendations.extend([
        "Monitor weather conditions regularly",
        "Apply fertilizer based on soil test results",
        "Practice crop rotation for soil health"
    ])
    
    return {
        "recommendations": recommendations[:5],  # Limit to 5 recommendations
        "risk_level": risk_level,
        "risk_reason": risk_reason,
        "fallback": True
    }


def clear_advisor_cache():
    """Clear the advisor cache - useful for testing or reloading."""
    global _advisor
    _advisor = None