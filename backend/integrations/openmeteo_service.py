"""
Open-Meteo Weather & Climate Service
Retrieves real historical weather, daily precipitation, temperature min/max, and soil moisture telemetry from Open-Meteo APIs.
"""

import urllib.request
import urllib.parse
import json
import datetime
from typing import Dict, Any, Optional

class OpenMeteoWeatherService:
    def __init__(self):
        self.archive_url = "https://archive-api.open-meteo.com/v1/archive"
        self.forecast_url = "https://api.open-meteo.com/v1/forecast"

    def fetch_weather_telemetry(
        self,
        lat: float,
        lng: float,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Fetches daily historical and forecast weather variables from Open-Meteo.
        """
        # Validate input coordinates
        if not (-90.0 <= lat <= 90.0 and -180.0 <= lng <= 180.0):
            return {
                "status": "ERROR",
                "error": "Invalid geographical coordinates. Latitude must be in [-90, 90] and Longitude in [-180, 180].",
                "lat": lat,
                "lng": lng
            }

        # Default date range: last 90 days
        today = datetime.date.today()
        if not end_date:
            end_date = today.strftime("%Y-%m-%d")
        if not start_date:
            start_date = (today - datetime.timedelta(days=90)).strftime("%Y-%m-%d")

        # Determine whether to use archive API (past dates) or forecast API (recent/future)
        start_dt = datetime.datetime.strptime(start_date, "%Y-%m-%d").date()
        end_dt = datetime.datetime.strptime(end_date, "%Y-%m-%d").date()

        # Archive endpoint is ideal for historical dates older than 5 days ago
        target_url = self.archive_url if end_dt < (today - datetime.timedelta(days=5)) else self.forecast_url

        params = {
            "latitude": lat,
            "longitude": lng,
            "start_date": start_date,
            "end_date": end_date,
            "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,soil_moisture_0_to_7cm_mean",
            "timezone": "auto"
        }

        query_string = urllib.parse.urlencode(params)
        full_url = f"{target_url}?{query_string}"

        try:
            req = urllib.request.Request(
                full_url,
                headers={"User-Agent": "NABARD-Climate-Risk-Engine/2.0"}
            )
            with urllib.request.urlopen(req, timeout=8) as response:
                payload = json.loads(response.read().decode('utf-8'))
                
                daily = payload.get("daily", {})
                dates = daily.get("time", [])
                t_max = daily.get("temperature_2m_max", [])
                t_min = daily.get("temperature_2m_min", [])
                precip = daily.get("precipitation_sum", [])
                soil_m = daily.get("soil_moisture_0_to_7cm_mean", [])

                # Clean null values
                valid_t_max = [t for t in t_max if t is not None]
                valid_t_min = [t for t in t_min if t is not None]
                valid_precip = [p for p in precip if p is not None]
                valid_soil = [s for s in soil_m if s is not None]

                total_rain_mm = round(sum(valid_precip), 1) if valid_precip else 0.0
                avg_t_max = round(sum(valid_t_max) / len(valid_t_max), 1) if valid_t_max else 0.0
                avg_t_min = round(sum(valid_t_min) / len(valid_t_min), 1) if valid_t_min else 0.0
                mean_soil = round(sum(valid_soil) / len(valid_soil), 3) if valid_soil else 0.0
                heatwave_days = sum(1 for t in valid_t_max if t >= 35.0)

                # Estimate rainfall deficit relative to seasonal baseline (e.g. 450mm baseline)
                baseline_rainfall_mm = 450.0
                rainfall_deficit_pct = round(((total_rain_mm - baseline_rainfall_mm) / baseline_rainfall_mm) * 100.0, 1)

                return {
                    "status": "SUCCESS",
                    "source": "Open-Meteo Reanalysis & Forecast API",
                    "dataNature": "Model Reanalysis (ERA5-Land) / Atmospheric Forecast",
                    "lat": round(lat, 4),
                    "lng": round(lng, 4),
                    "startDate": start_date,
                    "endDate": end_date,
                    "summary": {
                        "totalPrecipitationMm": total_rain_mm,
                        "avgTempMaxC": avg_t_max,
                        "avgTempMinC": avg_t_min,
                        "meanSoilMoistureIndex": mean_soil,
                        "heatwaveDaysCount": heatwave_days,
                        "estimatedRainfallDeficitPct": rainfall_deficit_pct,
                        "droughtRiskCategory": "High" if rainfall_deficit_pct < -25 else "Moderate" if rainfall_deficit_pct < -10 else "Low"
                    },
                    "dailySeries": [
                        {
                            "date": dates[i],
                            "tempMax": t_max[i] if i < len(t_max) else None,
                            "tempMin": t_min[i] if i < len(t_min) else None,
                            "precipitationMm": precip[i] if i < len(precip) else None,
                            "soilMoisture": soil_m[i] if i < len(soil_m) else None
                        }
                        for i in range(len(dates))
                    ],
                    "timestamp": datetime.datetime.now().isoformat()
                }

        except Exception as e:
            return {
                "status": "ERROR",
                "error": f"Open-Meteo API Request Failed: {str(e)}",
                "lat": lat,
                "lng": lng,
                "startDate": start_date,
                "endDate": end_date
            }
