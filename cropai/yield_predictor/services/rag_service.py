from typing import Dict, Any
from django.conf import settings

_advisor = None
_ollama_service = None


def _get_ollama_service():
    """Lazy-load the Ollama service (local Qwen via Docker)."""
    global _ollama_service
    if _ollama_service is None:
        ollama_url = getattr(settings, 'OLLAMA_URL', None)
        ollama_model = getattr(settings, 'OLLAMA_MODEL', None)
        if ollama_url:
            try:
                from .ollama_service import OllamaRecommendationService
                _ollama_service = OllamaRecommendationService(
                    base_url=ollama_url,
                    model=ollama_model or "qwen3.5:0.8b",
                )
            except Exception as e:
                import logging
                logging.getLogger(__name__).warning(f"Ollama service init failed: {e}")
    return _ollama_service


def get_advisor():
    """Get or create the CropAdvisorRAG instance (legacy local model)."""
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
    Get AI recommendations with fallback chain:
    1. Ollama (local Docker Qwen) — fastest, no GPU needed
    2. Local Qwen RAG model — requires GPU/MPS
    3. Rule-based engine — always available
    """
    # 1. Try Ollama (Docker container)
    ollama = _get_ollama_service()
    if ollama and ollama.is_ready:
        try:
            result = ollama.get_recommendations(prediction_data)
            if result.get("recommendations"):
                return result
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"Ollama recommendation failed: {e}")

    # 2. Try local Qwen RAG model
    global _advisor
    if _advisor is not None and _advisor.model_ready:
        try:
            result = _advisor.get_recommendations(prediction_data)
            if result.get("recommendations"):
                result["model_source"] = "Qwen3.5-RAG (local)"
                return result
        except Exception:
            pass

    # 3. Fall back to rule-based recommendations
    from .prediction_service import _generate_rule_based_recommendations
    return _generate_rule_based_recommendations(prediction_data)


def is_model_ready() -> bool:
    """Check if the Qwen model is loaded and ready."""
    global _advisor
    if _advisor is None:
        return False
    return _advisor.model_ready


def is_rag_ready() -> bool:
    """Check if RAG components (embedder + FAISS index + docs) are loaded."""
    global _advisor
    if _advisor is None:
        return False
    return _advisor.rag_ready


def get_model_status() -> Dict[str, Any]:
    """Return detailed model status for health checks."""
    global _advisor
    if _advisor is None:
        return {
            "loaded": False,
            "model_ready": False,
            "rag_ready": False,
            "device": None,
            "lora_path": str(settings.QWEN_MODEL_PATH),
            "rag_data_path": str(settings.RAG_DATA_DIR),
        }
    return {
        "loaded": True,
        "model_ready": _advisor.model_ready,
        "rag_ready": _advisor.rag_ready,
        "device": str(_advisor.model.device) if _advisor.model else None,
        "lora_path": str(settings.QWEN_MODEL_PATH),
        "rag_data_path": str(settings.RAG_DATA_DIR),
        "document_count": len(_advisor.documents) if _advisor.documents else 0,
    }


def clear_advisor_cache():
    """Clear the advisor cache - useful for testing or reloading."""
    global _advisor
    _advisor = None