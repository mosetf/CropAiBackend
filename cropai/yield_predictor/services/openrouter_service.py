"""
OpenRouter API service for LLM-based crop recommendations.
Uses Qwen 3 via OpenRouter API — lightweight, no local GPU/Docker needed.
"""
import logging
from typing import Dict, Any, List
import requests

logger = logging.getLogger(__name__)

# OpenRouter API endpoints
OPENROUTER_API_URL = "https://openrouter.io/api/v1/chat/completions"
DEFAULT_MODEL = "qwen/qwen3-next-80b-a3b-instruct:free" 

class OpenRouterRecommendationService:
    """Generates crop recommendations using OpenRouter's Qwen 3 API."""

    def __init__(self, api_key: str, model: str = None):
        """
        Initialize OpenRouter service.

        Args:
            api_key: OpenRouter API key (get from https://openrouter.io/keys)
            model: Model to use (defaults to free Qwen 3)
        """
        if not api_key:
            raise ValueError("OpenRouter API key is required")
        
        self.api_key = api_key
        self.model = model or DEFAULT_MODEL
        self._ready = False
        self._check_ready()

    def _check_ready(self):
        """Check if OpenRouter API is accessible."""
        try:
            headers = self._get_headers()
            # Simple health check - just verify headers are valid
            resp = requests.get(
                "https://openrouter.io/api/v1/models",
                headers=headers,
                timeout=10
            )
            if resp.status_code == 200:
                self._ready = True
                logger.info(f"OpenRouter ready with model: {self.model}")
                return
            else:
                logger.warning(f"OpenRouter health check failed: {resp.status_code}")
        except Exception as e:
            logger.warning(f"OpenRouter not reachable: {e}")

    @property
    def is_ready(self) -> bool:
        return self._ready

    def _get_headers(self) -> Dict[str, str]:
        """Get request headers for OpenRouter API."""
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://cropai.synfusion.org", 
            "X-Title": "CropAI Yield Prediction System",
        }

    def get_recommendations(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate agricultural recommendations using OpenRouter's Qwen 3.

        Args:
            context: Dict with crop, location, yield, temp, rainfall, soil_ph, etc.

        Returns:
            Dict with recommendations (list), risk_level, risk_reason
        """
        if not self._ready:
            raise RuntimeError("OpenRouter service not ready or API key invalid")

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
            response = requests.post(
                OPENROUTER_API_URL,
                headers=self._get_headers(),
                json={
                    "model": self.model,
                    "messages": [
                        {
                            "role": "user",
                            "content": prompt,
                        }
                    ],
                    "temperature": 0.7,
                    "top_p": 0.9,
                    "max_tokens": 300,
                },
                timeout=60,
            )
            response.raise_for_status()
            
            data = response.json()
            text = data.get("choices", [{}])[0].get("message", {}).get("content", "").strip()

            if not text:
                raise ValueError("Empty response from OpenRouter")

            recommendations = self._parse_recommendations(text)
            risk_level, risk_reason = self._assess_risk(context)

            return {
                "recommendations": recommendations,
                "risk_level": risk_level,
                "risk_reason": risk_reason,
                "fallback": False,
                "model_source": f"OpenRouter/{self.model}",
            }

        except requests.exceptions.Timeout:
            logger.error("OpenRouter API call timed out")
            raise RuntimeError("OpenRouter API timeout")
        except requests.exceptions.HTTPError as e:
            logger.error(f"OpenRouter API error: {e.response.status_code} {e.response.text}")
            raise RuntimeError(f"OpenRouter API error: {e.response.status_code}")
        except Exception as e:
            logger.error(f"OpenRouter recommendation failed: {e}")
            raise

    def _parse_recommendations(self, text: str) -> List[str]:
        """Parse numbered recommendations from model response."""
        import re
        lines = text.split('\n')
        recommendations = []

        for line in lines:
            line = line.strip()
            # Remove numbering (1., 1), etc.)
            line = re.sub(r'^\d+[\.\)]\s*', '', line)
            # Clean up markdown bold
            line = re.sub(r'\*\*([^*]+)\*\*[:\s]*', r'\1: ', line)
            line = line.strip()
            if len(line) > 25 and not line.endswith(':'):
                recommendations.append(line)

        return recommendations[:3]  # Return max 3 recommendations

    def _assess_risk(self, context: Dict[str, Any]) -> tuple:
        """Assess risk level based on context."""
        yield_pred = context.get("yield", 0)
        rainfall = context.get("rainfall", 500)
        soil_ph = context.get("soil_ph", 6.5)

        risk_factors = 0

        if yield_pred < 1.5:
            risk_factors += 1
        if rainfall < 400 or rainfall > 800:
            risk_factors += 1
        if soil_ph < 5.5 or soil_ph > 7.5:
            risk_factors += 1

        if risk_factors == 0:
            return "low", "Optimal conditions detected"
        elif risk_factors == 1:
            return "medium", "Some environmental stress detected"
        else:
            return "high", "Multiple risk factors identified"
