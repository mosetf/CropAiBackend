from typing import Dict, Any
from datetime import date, datetime, timedelta
import pandas as pd

from ..utils.model_loader import get_model, get_season_encoder
from .weather_service import get_current_weather, get_forecast, build_seasonal_features, WeatherUnavailableError
from .rag_service import get_recommendations

class _NoOp:
    def __getattr__(self, name):
        def noop(*args, **kwargs):
            pass
        return noop

logger = _NoOp()

LOCATION_COORDS = {
    # ── NAIROBI METROPOLITAN ──────────────────────────────
    "Nairobi":          {"lat": -1.2864, "lon": 36.8172, "elevation_m": 1795, "region": "Nairobi Metropolitan"},
    "Kiambu":           {"lat": -1.0314, "lon": 36.8310, "elevation_m": 1600, "region": "Nairobi Metropolitan"},
    "Murang'a":         {"lat": -0.7193, "lon": 37.1551, "elevation_m": 1530, "region": "Nairobi Metropolitan"},
    "Nyeri":            {"lat": -0.4167, "lon": 36.9500, "elevation_m": 1759, "region": "Nairobi Metropolitan"},
    "Kirinyaga":        {"lat": -0.5593, "lon": 37.2982, "elevation_m": 1200, "region": "Nairobi Metropolitan"},

    # ── CENTRAL RIFT ──────────────────────────────────────
    "Nakuru":           {"lat": -0.3031, "lon": 36.0800, "elevation_m": 1850, "region": "Central Rift"},
    "Narok":            {"lat": -1.0833, "lon": 35.8667, "elevation_m": 1890, "region": "Central Rift"},
    "Laikipia":         {"lat":  0.3606, "lon": 36.7820, "elevation_m": 1740, "region": "Central Rift"},
    "Nyandarua":        {"lat": -0.1800, "lon": 36.5200, "elevation_m": 2300, "region": "Central Rift"},
    "Baringo":          {"lat":  0.4700, "lon": 35.9700, "elevation_m": 1200, "region": "Central Rift"},
    "Kajiado":          {"lat": -2.0980, "lon": 36.7760, "elevation_m": 1600, "region": "Central Rift"},

    # ── NORTH RIFT ────────────────────────────────────────
    "Uasin Gishu":      {"lat":  0.5200, "lon": 35.2800, "elevation_m": 2100, "region": "North Rift"},
    "Trans Nzoia":      {"lat":  1.0500, "lon": 34.9500, "elevation_m": 1850, "region": "North Rift"},
    "Elgeyo Marakwet":  {"lat":  0.8500, "lon": 35.5000, "elevation_m": 2000, "region": "North Rift"},
    "Nandi":            {"lat":  0.1833, "lon": 35.1167, "elevation_m": 1900, "region": "North Rift"},
    "West Pokot":       {"lat":  1.6200, "lon": 35.1200, "elevation_m": 1450, "region": "North Rift"},
    "Turkana":          {"lat":  3.1300, "lon": 35.5600, "elevation_m":  450, "region": "North Rift"},
    "Samburu":          {"lat":  1.2140, "lon": 36.5280, "elevation_m": 1000, "region": "North Rift"},

    # ── SOUTH RIFT ────────────────────────────────────────
    "Kericho":          {"lat": -0.3686, "lon": 35.2863, "elevation_m": 2010, "region": "South Rift"},
    "Bomet":            {"lat": -0.7867, "lon": 35.3427, "elevation_m": 2030, "region": "South Rift"},
    "Kisii":            {"lat": -0.6817, "lon": 34.7667, "elevation_m": 1670, "region": "South Rift"},
    "Nyamira":          {"lat": -0.5670, "lon": 34.9350, "elevation_m": 1800, "region": "South Rift"},

    # ── WESTERN ───────────────────────────────────────────
    "Kakamega":         {"lat":  0.2827, "lon": 34.7519, "elevation_m": 1535, "region": "Western"},
    "Bungoma":          {"lat":  0.5635, "lon": 34.5606, "elevation_m": 1525, "region": "Western"},
    "Busia":            {"lat":  0.4600, "lon": 34.1100, "elevation_m": 1140, "region": "Western"},
    "Vihiga":           {"lat":  0.0781, "lon": 34.7232, "elevation_m": 1530, "region": "Western"},

    # ── NYANZA ────────────────────────────────────────────
    "Kisumu":           {"lat": -0.0917, "lon": 34.7679, "elevation_m": 1131, "region": "Nyanza"},
    "Siaya":            {"lat": -0.0610, "lon": 34.2880, "elevation_m": 1170, "region": "Nyanza"},
    "Homa Bay":         {"lat": -0.5167, "lon": 34.4667, "elevation_m": 1170, "region": "Nyanza"},
    "Migori":           {"lat": -1.0634, "lon": 34.4731, "elevation_m": 1520, "region": "Nyanza"},

    # ── EASTERN ───────────────────────────────────────────
    "Meru":             {"lat":  0.0467, "lon": 37.6495, "elevation_m": 1500, "region": "Eastern"},
    "Embu":             {"lat": -0.5333, "lon": 37.4500, "elevation_m": 1400, "region": "Eastern"},
    "Tharaka Nithi":    {"lat": -0.2900, "lon": 37.9300, "elevation_m": 1000, "region": "Eastern"},
    "Kitui":            {"lat": -1.3667, "lon": 38.0167, "elevation_m":  976, "region": "Eastern"},
    "Machakos":         {"lat": -1.5177, "lon": 37.2634, "elevation_m": 1600, "region": "Eastern"},
    "Makueni":          {"lat": -1.8036, "lon": 37.6236, "elevation_m": 1000, "region": "Eastern"},
    "Isiolo":           {"lat":  0.3540, "lon": 37.5820, "elevation_m":  900, "region": "Eastern"},
    "Marsabit":         {"lat":  2.3280, "lon": 37.9940, "elevation_m":  750, "region": "Eastern"},

    # ── COAST ─────────────────────────────────────────────
    "Mombasa":          {"lat": -4.0435, "lon": 39.6682, "elevation_m":   17, "region": "Coast"},
    "Kilifi":           {"lat": -3.5107, "lon": 39.9093, "elevation_m":   25, "region": "Coast"},
    "Kwale":            {"lat": -4.1770, "lon": 39.4600, "elevation_m":  200, "region": "Coast"},
    "Taita Taveta":     {"lat": -3.4000, "lon": 38.3500, "elevation_m":  600, "region": "Coast"},
    "Lamu":             {"lat": -2.2690, "lon": 40.9020, "elevation_m":    5, "region": "Coast"},
    "Tana River":       {"lat": -1.0000, "lon": 40.0000, "elevation_m":  100, "region": "Coast"},

    # ── NORTH EASTERN ─────────────────────────────────────
    "Garissa":          {"lat": -0.4532, "lon": 39.6461, "elevation_m":  150, "region": "North Eastern"},
    "Wajir":            {"lat":  1.7500, "lon": 40.0667, "elevation_m":  244, "region": "North Eastern"},
    "Mandera":          {"lat":  3.9366, "lon": 41.8670, "elevation_m":  328, "region": "North Eastern"},
}

FEATURES = [
    "lat", "lon", "elevation_m",
    "temp_avg_c", "temp_max_c", "temp_min_c", "temp_range_c",
    "heat_stress_days", "cold_stress_days",
    "rainfall_mm", "rainfall_days", "dry_spell_days",
    "humidity_pct", "solar_mj", "gdd_base10",
    "soil_ph", "organic_carbon", "clay_pct", "sand_pct",
    "fertilizer_kg_ha", "planting_month",
    "year", "season_encoded",
]


def run_prediction(
    crop: str, 
    location: str, 
    soil_data: Dict[str, float],
    fertilizer: float, 
    planting_date: date,
    api_settings: Dict[str, str],
    market_price_override: float = None,
    labour_cost_override: float = None,
) -> Dict[str, Any]:
    """
    Orchestrates the full prediction pipeline.
    
    Args:
        crop: Crop type (maize, beans, etc.)
        location: Kenya location name
        soil_data: Dict with keys: soil_ph, organic_carbon, soil_moisture
        fertilizer: Fertilizer amount in kg/ha
        planting_date: Date object for planting
        api_settings: Dict with weather API keys/URLs
    
    Returns:
        Dict with prediction results:
        {
            'success': bool,
            'predicted_yield': float,
            'yield_range': [float, float],
            'harvest_window': str,
            'net_profit': float,
            'weather_data': dict,
            'ai_recommendations': list,
            'risk_level': str,
            'risk_reason': str,
            'model_source': str,
            'fallback_used': bool,
            'error': str (if success=False)
        }
    """
    
    try:
        logger.info(f"🌾 Starting prediction pipeline")
        logger.info(f" INPUT: crop={crop}, location={location}, planting_date={planting_date}")
        logger.info(f" INPUT: soil_data={soil_data}, fertilizer={fertilizer}")
        
        if location not in LOCATION_COORDS:
            logger.error(f"Unknown location: {location}")
            return {"success": False, "error": f"Unknown location: {location}"}
            
        loc_info = LOCATION_COORDS[location]
        logger.info(f" Location info: lat={loc_info['lat']}, lon={loc_info['lon']}, elevation={loc_info['elevation_m']}m")
        
        logger.info(f" Loading XGBoost model for {crop}")
        model = get_model(crop)
        season_encoder = get_season_encoder()
        logger.info(f"Model loaded successfully")
        
        logger.info(f" Fetching weather data for {location}")
        try:
            current_weather = get_current_weather(
                location, 
                loc_info["lat"], 
                loc_info["lon"],
                api_settings.get("api_key"),
                api_settings.get("base_url")
            )
            logger.info(f" Current weather: {current_weather}")
            
            forecast_data = get_forecast(
                loc_info["lat"],
                loc_info["lon"], 
                api_settings.get("api_key"),
                api_settings.get("forecast_url")
            )
            if forecast_data:
                if isinstance(forecast_data, dict):
                    logger.info(f" Forecast data keys: {list(forecast_data.keys())}")
                elif isinstance(forecast_data, list):
                    logger.info(f" Forecast data: list with {len(forecast_data)} items")
                else:
                    logger.info(f" Forecast data type: {type(forecast_data)}")
            else:
                logger.info(f" Forecast data: None")
            
            weather_features = build_seasonal_features(current_weather, forecast_data)
            weather_fallback = current_weather.get("used_fallback", False)
            logger.info(f" Weather features: {weather_features}")
            
        except WeatherUnavailableError:
            logger.warning(f"  Weather unavailable for {location}, using defaults")
            weather_features = {
                "temp_avg_c": 22.0, "temp_min_c": 18.0, "temp_max_c": 26.0,
                "rainfall_season_mm": 800.0, "humidity_pct": 65.0,
                "rainfall_days": 30, "dry_spell_days": 5, "solar_mj": 18.0
            }
            current_weather = {"temperature": 22.0, "humidity": 65.0, "rainfall": 800.0}
            weather_fallback = True
        
        logger.info(f" Building feature vector")
        planting_month = planting_date.month
        season = "long_rains" if planting_month in [3, 4, 5] else "short_rains"
        season_encoded = season_encoder.transform([season])[0]
        logger.info(f"Planting: month={planting_month}, season={season}, encoded={season_encoded}")
        
        features = {
            "lat": loc_info["lat"],
            "lon": loc_info["lon"],
            "elevation_m": loc_info["elevation_m"],
            "temp_avg_c": weather_features["temp_avg_c"],
            "temp_max_c": weather_features["temp_max_c"],
            "temp_min_c": weather_features["temp_min_c"],
            "temp_range_c": weather_features["temp_max_c"] - weather_features["temp_min_c"],
            "heat_stress_days": max(0, (weather_features["temp_max_c"] - 32) * 2),
            "cold_stress_days": max(0, (12 - weather_features["temp_min_c"]) * 1),
            "rainfall_mm": weather_features["rainfall_season_mm"],
            "rainfall_days": weather_features["rainfall_days"],
            "dry_spell_days": weather_features["dry_spell_days"],
            "humidity_pct": weather_features["humidity_pct"],
            "solar_mj": weather_features["solar_mj"],
            "gdd_base10": max(0, (weather_features["temp_avg_c"] - 10)) * 90,
            "soil_ph": soil_data.get("soil_ph", 6.0),
            "organic_carbon": soil_data.get("organic_carbon", 1.5),
            "clay_pct": 30.0,  # default; could be improved with SoilGrids API
            "sand_pct": 40.0,  # default
            "fertilizer_kg_ha": fertilizer,
            "planting_month": planting_month,
            "year": planting_date.year,
            "season_encoded": season_encoded,
        }
        
        logger.info(f" FEATURES: {features}")
        
        logger.info(f" Preparing features for model prediction")
        X = pd.DataFrame([features])[FEATURES]
        logger.info(f" Feature vector shape: {X.shape}")
        logger.info(f" Feature vector:\n{X.iloc[0].to_dict()}")
        
        logger.info(f" Running XGBoost prediction...")
        yield_pred = float(model.predict(X)[0])
        logger.info(f"MODEL OUTPUT: {yield_pred:.3f} tonnes/hectare")
        
        yield_low = round(yield_pred * 0.85, 2)
        yield_high = round(yield_pred * 1.15, 2)
        logger.info(f" Confidence interval: [{yield_low}, {yield_high}] t/ha")
        
        # 7. Get RAG-based AI recommendations
        logger.info(f"Getting AI recommendations...")
        try:
            ai_result = get_recommendations({
                "crop": crop,
                "location": location,
                "yield": yield_pred,
                "temp": weather_features["temp_avg_c"],
                "rainfall": weather_features["rainfall_season_mm"],
                "soil_ph": soil_data.get("soil_ph", 6.0),
                "fertilizer": fertilizer,
            })
            logger.info(f"AI recommendations: {ai_result.get('recommendations', [])}")
        except Exception as e:
            logger.warning(f"  RAG recommendations failed: {e}")
            ai_result = {
                "recommendations": ["Plant early for optimal yield", "Monitor weather conditions", "Apply balanced fertilizer"],
                "risk_level": "medium",
                "risk_reason": "Normal growing conditions expected",
                "fallback": True
            }
        
        # 8. Calculate business metrics
        logger.info(f" Calculating business metrics...")
        harvest_window = _estimate_harvest_window(planting_date, crop)
        net_profit = _estimate_profit(yield_pred, crop, market_price_override, labour_cost_override)
        logger.info(f" Harvest window: {harvest_window}, Net profit: ${net_profit}")
        
        result = {
            "success": True,
            "predicted_yield": round(yield_pred, 2),
            "yield_range": [yield_low, yield_high],
            "harvest_window": harvest_window,
            "net_profit": net_profit,
            "weather_data": {
                "temp": weather_features["temp_avg_c"],
                "rainfall": weather_features["rainfall_season_mm"],
                "humidity": weather_features["humidity_pct"],
            },
            "ai_recommendations": ai_result.get("recommendations", []),
            "risk_level": ai_result.get("risk_level", "medium"),
            "risk_reason": ai_result.get("risk_reason", ""),
            "model_source": "XGBoost + Qwen3.5-RAG",
            "fallback_used": weather_fallback or ai_result.get("fallback", False),
        }
        
        logger.info(f"PREDICTION COMPLETE: {result}")
        return result
        
    except FileNotFoundError as e:
        error_msg = f"Model not found for {crop}: {e}"
        logger.error(f"{error_msg}")
        return {"success": False, "error": error_msg}
    except Exception as e:
        error_msg = f"Prediction failed: {str(e)}"
        logger.error(f"Prediction failed for {crop} at {location}: {e}", exc_info=True)
        return {"success": False, "error": error_msg}


def _estimate_harvest_window(planting_date: date, crop: str) -> str:
    """Estimate harvest window based on crop type and planting date."""
    days_to_maturity = {
        "maize": 110, "beans": 70, "wheat": 120,
        "sorghum": 100, "coffee": 300, "tea": 365, "potatoes": 90,
        "cassava": 300, "rice": 120,
    }
    
    dtm = days_to_maturity.get(crop, 100)
    harvest_start = planting_date + timedelta(days=dtm - 10)
    harvest_end = planting_date + timedelta(days=dtm + 10)
    
    return f"{harvest_start.strftime('%B %d, %Y')} to {harvest_end.strftime('%B %d, %Y')}"


def _estimate_profit(
    yield_t_ha: float, 
    crop: str,
    market_price_override: float = None,
    labour_cost_override: float = None,
) -> float:
    """Estimate profit using current Kenya market prices."""
    # Prices in KES per tonne (approximate 2026 farm-gate)
    market_prices = {
        "maize": 35_000, "beans": 90_000, "wheat": 40_000,
        "sorghum": 30_000, "coffee": 250_000, "tea": 60_000, 
        "potatoes": 25_000, "cassava": 20_000, "rice": 45_000,
    }
    cost_per_ha = {
        "maize": 25_000, "beans": 20_000, "wheat": 30_000,
        "sorghum": 18_000, "coffee": 80_000, "tea": 45_000, 
        "potatoes": 35_000, "cassava": 15_000, "rice": 30_000,
    }
    
    price = market_price_override if market_price_override else market_prices.get(crop, 35_000)
    cost = cost_per_ha.get(crop, 25_000)
    
    if labour_cost_override:
        cost += labour_cost_override
    
    return round((yield_t_ha * price) - cost, 2)