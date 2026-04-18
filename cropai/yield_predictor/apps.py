import logging
from django.apps import AppConfig

logger = logging.getLogger(__name__)


class YieldPredictorConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'yield_predictor'

    def ready(self):
        """
        Preload models at Django startup.
        Priority: Ollama (Docker) > Local Qwen RAG > XGBoost only.
        """
        import threading

        def _preload_models():
            try:
                # Preload XGBoost models
                from .utils.model_loader import get_model, get_season_encoder
                logger.info("Warming up XGBoost model cache…")
                try:
                    get_model('maize')
                    get_season_encoder()
                    logger.info("XGBoost models loaded successfully.")
                except Exception as e:
                    logger.warning(f"XGBoost model preload warning: {e}")

                # Try Ollama first (Docker container)
                from .services.rag_service import _get_ollama_service, get_model_status
                ollama = _get_ollama_service()
                if ollama and ollama.is_ready:
                    logger.info(f"Ollama ready with model: {ollama.model}")
                else:
                    logger.info("Ollama not available. Will use rule-based recommendations.")

                # Don't try to load the local Qwen model — it segfaults on macOS.
                # On Linux with GPU, uncomment the block below:
                # from .services.rag_service import get_advisor
                # advisor = get_advisor()
                # if advisor.model_ready:
                #     logger.info(f"Local Qwen model loaded on {advisor.model.device}")

                status = get_model_status()
                logger.info(f"Model status: {status}")

            except Exception as e:
                logger.error(f"Model preload failed: {e}. Rule-based fallback will be used.")

        t = threading.Thread(target=_preload_models, daemon=True)
        t.start()
