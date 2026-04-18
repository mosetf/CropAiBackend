"""
Ollama API service for LLM-based crop recommendations.
Runs Qwen locally in a Docker container — no API key needed, no external calls.
"""
import logging
from typing import Dict, Any, List
import requests

logger = logging.getLogger(__name__)

# Default Ollama URL — overridden by OLLAMA_URL env var in docker-compose
DEFAULT_OLLAMA_URL = "http://localhost:11434"
DEFAULT_MODEL = "qwen3.5:0.8b"


class OllamaRecommendationService:
    """Generates crop recommendations using Ollama (local Qwen via Docker)."""

    def __init__(self, base_url: str = None, model: str = None):
        self.base_url = (base_url or DEFAULT_OLLAMA_URL).rstrip("/")
        self.model = model or DEFAULT_MODEL
        self._ready = False
        self._check_ready()

    def _check_ready(self):
        """Check if Ollama is running and the model is available."""
        try:
            resp = requests.get(f"{self.base_url}/api/tags", timeout=5)
            if resp.status_code == 200:
                models = [m.get("name", "") for m in resp.json().get("models", [])]
                if self.model in models:
                    self._ready = True
                    logger.info(f"Ollama ready with model: {self.model}")
                    return
                else:
                    logger.warning(
                        f"Model {self.model} not found in Ollama. "
                        f"Available: {models}. "
                        f"Run: docker exec cropai-ollama ollama pull {self.model}"
                    )
            else:
                logger.warning(f"Ollama health check failed: {resp.status_code}")
        except Exception as e:
            logger.warning(f"Ollama not reachable at {self.base_url}: {e}")

    @property
    def is_ready(self) -> bool:
        return self._ready

    def pull_model(self) -> bool:
        """Pull the model into Ollama if not already present."""
        try:
            resp = requests.post(
                f"{self.base_url}/api/pull",
                json={"name": self.model},
                timeout=120,
            )
            if resp.status_code == 200:
                self._ready = True
                logger.info(f"Model {self.model} pulled successfully")
                return True
            logger.warning(f"Failed to pull model: {resp.status_code} {resp.text}")
            return False
        except Exception as e:
            logger.error(f"Error pulling model: {e}")
            return False

    def get_recommendations(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate agricultural recommendations using Ollama API.

        Args:
            context: Dict with crop, location, yield, temp, rainfall, soil_ph, fertilizer

        Returns:
            Dict with recommendations (list), risk_level, risk_reason
        """
        if not self._ready:
            raise RuntimeError("Ollama service not ready or model not loaded")

        crop = context.get("crop", "maize")
        location = context.get("location", "")
        yield_pred = context.get("yield", 0)
        temp = context.get("temp", 20)
        rainfall = context.get("rainfall", 500)
        soil_ph = context.get("soil_ph", 6.5)
        fertilizer = context.get("fertilizer", 100)
        humidity = context.get("humidity", 65)
        organic_carbon = context.get("organic_carbon", 1.5)

        prompt = (
            f"You are an agricultural advisor for Kenyan smallholder farmers.\n"
            f"Give 3 specific, actionable recommendations with exact quantities and timelines.\n"
            f"Do NOT give generic advice like 'monitor weather' or 'apply balanced fertilizer'.\n\n"
            f"Crop: {crop}\n"
            f"Location: {location}, Kenya\n"
            f"Predicted yield: {yield_pred:.2f} t/ha\n"
            f"Temperature: {temp:.1f}°C | Rainfall: {rainfall:.0f}mm | Humidity: {humidity:.0f}%\n"
            f"Soil pH: {soil_ph:.1f} | Organic carbon: {organic_carbon:.1f}%\n"
            f"Fertilizer: {fertilizer:.0f} kg/ha\n"
            f"Planting date: {context.get('planting_date', 'N/A')}\n\n"
            f"Provide exactly 3 numbered recommendations:"
        )

        try:
            resp = requests.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.7,
                        "top_p": 0.9,
                        "num_predict": 300,
                    },
                },
                timeout=60,
            )
            resp.raise_for_status()
            text = resp.json().get("response", "").strip()

            recommendations = self._parse_recommendations(text)
            risk_level, risk_reason = self._assess_risk(context)

            return {
                "recommendations": recommendations,
                "risk_level": risk_level,
                "risk_reason": risk_reason,
                "fallback": False,
                "model_source": f"Ollama/{self.model}",
            }

        except Exception as e:
            logger.warning(f"Ollama API call failed: {e}")
            raise

    def _parse_recommendations(self, text: str) -> List[str]:
        """Parse numbered recommendations from model response."""
        import re
        lines = text.split('\n')
        recommendations = []

        for line in lines:
            line = line.strip()
            line = re.sub(r'^\d+[\.\)]\s*', '', line)
            line = re.sub(r'\*\*([^*]+)\*\*[:\s]*', r'\1: ', line)
            line = line.strip()
            if len(line) > 25 and not line.endswith(':'):
                recommendations.append(line)
            if len(recommendations) >= 3:
                break

        return recommendations[:3] if recommendations else [
            f"Apply 120 kg/ha nitrogen in split doses for optimal maize growth",
            "Test soil pH and adjust with lime or sulfur as needed",
            "Monitor crop development stages and apply top-dressing at vegetative stage"
        ]

    def _assess_risk(self, context: Dict[str, Any]) -> tuple:
        """Assess risk level based on environmental factors."""
        temp = context.get("temp", 20)
        rainfall = context.get("rainfall", 500)
        soil_ph = context.get("soil_ph", 6.5)
        humidity = context.get("humidity", 65)

        risk_factors = 0
        risk_reasons = []

        if temp < 12 or temp > 35:
            risk_factors += 1
            risk_reasons.append(f"Temperature stress at {temp:.1f}°C")
        if rainfall < 400:
            risk_factors += 1
            risk_reasons.append(f"Low seasonal rainfall ({rainfall:.0f}mm)")
        if rainfall > 1500:
            risk_factors += 1
            risk_reasons.append(f"Excess rainfall ({rainfall:.0f}mm) risks waterlogging")
        if soil_ph < 5.0 or soil_ph > 8.5:
            risk_factors += 1
            risk_reasons.append(f"Extreme soil pH ({soil_ph:.1f})")
        if humidity > 85:
            risk_factors += 1
            risk_reasons.append(f"High humidity ({humidity:.0f}%) increases disease risk")

        if risk_factors >= 3:
            return "high", "; ".join(risk_reasons) if risk_reasons else "Multiple stress factors"
        elif risk_factors >= 1:
            return "medium", "; ".join(risk_reasons) if risk_reasons else "Some conditions may affect growth"
        else:
            return "low", "Conditions are favorable for good yield"
