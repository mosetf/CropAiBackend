from typing import Dict, Any
from django.conf import settings

_advisor = None


def get_advisor():
    """Get or create the CropAdvisorRAG instance."""
    global _advisor
    if _advisor is None:
        from ..utils.crop_advisor_rag import CropAdvisorRAG
        
        _advisor = CropAdvisorRAG(
            model_path=str(settings.QWEN_MODEL_PATH),
            rag_data_path=str(settings.RAG_DATA_DIR)
        )
    
    return _advisor


def get_recommendations(prediction_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Get AI recommendations using RAG-enhanced Qwen model.
    
    Args:
        prediction_data: Dict with crop, location, yield, temp, rainfall, soil_ph, fertilizer
    
    Returns:
        Dict with recommendations, risk_level, risk_reason
    """
    advisor = get_advisor()
    result = advisor.get_recommendations(prediction_data)
    return result


def clear_advisor_cache():
    """Clear the advisor cache - useful for testing or reloading."""
    global _advisor
    _advisor = None