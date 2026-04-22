import logging
from typing import Dict, Any
from django.conf import settings

logger = logging.getLogger(__name__)

_openrouter_service = None


def _get_openrouter_service():
    """Lazy-load the OpenRouter service (cloud-hosted Qwen 3 Next)."""
    global _openrouter_service
    if _openrouter_service is None:
        api_key = getattr(settings, 'OPENROUTER_API_KEY', None)
        if not api_key:
            raise ValueError("OPENROUTER_API_KEY environment variable is not set")
        try:
            from .openrouter_service import OpenRouterRecommendationService
            model = getattr(settings, 'OPENROUTER_MODEL', 'qwen/qwen3-next-80b-a3b-instruct:free')
            _openrouter_service = OpenRouterRecommendationService(
                api_key=api_key,
                model=model,
            )
            logger.info(f"OpenRouter service initialized with model: {model}")
        except Exception as e:
            logger.error(f"Failed to initialize OpenRouter service: {e}")
            raise
    return _openrouter_service


def get_recommendations(prediction_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Get AI recommendations using OpenRouter's Qwen 3 Next 80B model.
    
    This is the primary (and only) method for generating recommendations.
    No fallbacks - OpenRouter must be configured with OPENROUTER_API_KEY.
    """
    openrouter = _get_openrouter_service()
    try:
        result = openrouter.get_recommendations(prediction_data)
        logger.info("Successfully generated recommendations using OpenRouter")
        return result
    except Exception as e:
        logger.error(f"OpenRouter recommendation failed: {e}")
        raise RuntimeError(f"Failed to generate recommendations: {str(e)}")


def is_model_ready() -> bool:
    """Check if OpenRouter service is ready."""
    try:
        openrouter = _get_openrouter_service()
        return openrouter.is_ready
    except Exception:
        return False


def get_model_status() -> Dict[str, Any]:
    """Return OpenRouter model status for health checks."""
    try:
        openrouter = _get_openrouter_service()
        return {
            "service": "OpenRouter",
            "model": openrouter.model,
            "is_ready": openrouter.is_ready,
            "api_configured": True,
        }
    except Exception as e:
        return {
            "service": "OpenRouter",
            "model": None,
            "is_ready": False,
            "api_configured": False,
            "error": str(e),
        }


def clear_service_cache():
    """Clear the service cache - useful for testing or reloading."""
    global _openrouter_service
    _openrouter_service = None
