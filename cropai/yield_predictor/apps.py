import logging
from django.apps import AppConfig

logger = logging.getLogger(__name__)


class YieldPredictorConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'yield_predictor'

    def ready(self):
        """
        Initialize services at Django startup.
        Uses OpenRouter (Qwen 3 Next 80B) for recommendations.
        """
        import threading

        def _initialize_services():
            try:
                from .utils.model_loader import get_model, get_season_encoder
                logger.info("Warming up XGBoost model cache…")
                try:
                    get_model('maize')
                    get_season_encoder()
                    logger.info("✓ XGBoost models loaded successfully.")
                except Exception as e:
                    logger.warning(f"XGBoost model preload warning: {e}")

                from .services.rag_service import get_model_status
                status = get_model_status()
                if status.get('is_ready'):
                    logger.info(f"✓ OpenRouter service ready: {status.get('model')}")
                else:
                    logger.warning(f"⚠ OpenRouter service not available: {status.get('error', 'Unknown error')}")
                    logger.warning("Ensure OPENROUTER_API_KEY environment variable is set.")

            except Exception as e:
                logger.error(f"Service initialization failed: {e}")

        t = threading.Thread(target=_initialize_services, daemon=True)
        t.start()
