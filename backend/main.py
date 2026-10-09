"""
NABARD Climate-Aware Credit Risk Application Backend Server
Exposes Phase 2 endpoints for real environmental telemetry: Open-Meteo Weather, Copernicus Sentinel-2 Satellite, and ISRIC SoilGrids.
"""

import os
import sys
import datetime
from typing import Dict, Any, Optional

# Add backend directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from integrations.openmeteo_service import OpenMeteoWeatherService
from integrations.landsat_service import NASALandsatService
from integrations.soilgrids_service import SoilGridsService

# Preserved engines
from integrations.sentinel_connector import SentinelHubConnector
from integrations.weather_connector import OpenMeteoWeatherConnector
from analytics.yield_predictor import XGBoostCropYieldPredictor
from analytics.risk_engine import ClimateCreditRiskEngine
from analytics.shap_explainability import SHAPExplainabilityEngine
from analytics.pdf_generator import PDFReportGenerator
from crop_data_service import router as crop_router
from risk_service import router as risk_router
from farmer_data_service import router as farmer_router
from auth_service import router as auth_router
from officer_service import router as officer_router

# Check FastAPI availability
try:
    from fastapi import FastAPI, HTTPException, Query
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import FileResponse
    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False

# Instantiate Phase 2 Services
weather_service = OpenMeteoWeatherService()
sentinel_service = NASALandsatService()
soil_service = SoilGridsService()

# Instantiate Preserved Engines
sentinel_connector = SentinelHubConnector()
weather_connector = OpenMeteoWeatherConnector()
yield_predictor = XGBoostCropYieldPredictor()
risk_engine = ClimateCreditRiskEngine()
shap_engine = SHAPExplainabilityEngine()
pdf_generator = PDFReportGenerator()

if FASTAPI_AVAILABLE:
    app = FastAPI(
        title="NABARD Climate Telemetry & Credit Risk API",
        description="Phase 2 Real Environmental Telemetry API: Open-Meteo Weather, Copernicus Sentinel-2, & ISRIC SoilGrids.",
        version="2.0.0"
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(auth_router)
    app.include_router(crop_router)
    app.include_router(risk_router)
    app.include_router(farmer_router)
    app.include_router(officer_router)

    # Mount Static Web Application Files
    from fastapi.staticfiles import StaticFiles
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    if os.path.exists(os.path.join(project_root, "css")):
        app.mount("/css", StaticFiles(directory=os.path.join(project_root, "css")), name="css")
    if os.path.exists(os.path.join(project_root, "js")):
        app.mount("/js", StaticFiles(directory=os.path.join(project_root, "js")), name="js")
    if os.path.exists(os.path.join(project_root, "data")):
        app.mount("/data", StaticFiles(directory=os.path.join(project_root, "data")), name="data")

    @app.get("/")
    def read_root():
        index_path = os.path.join(project_root, "index.html")
        if os.path.exists(index_path):
            return FileResponse(index_path)
        return {
            "system": "NABARD Climate-Aware Credit Risk System API",
            "phase": "Phase 2 Environmental Telemetry Active",
            "version": "2.0.0"
        }

    SPA_PAGE_ROUTES = {"auth", "dashboard", "loans", "crops", "climate", "risk", "officer"}

    @app.get("/auth/google/callback")
    @app.get("/auth/google/callback/")
    @app.get("/api/auth/google/callback")
    @app.get("/api/auth/google/callback/")
    def top_level_google_auth_callback(
        code: Optional[str] = Query(None),
        state: Optional[str] = Query(None),
        error: Optional[str] = Query(None),
        iss: Optional[str] = Query(None)
    ):
        from auth_service import google_auth_callback
        return google_auth_callback(code=code, state=state, error=error, iss=iss)

    @app.get("/{page_route}")
    def serve_spa_page(page_route: str):
        if page_route.lower() in SPA_PAGE_ROUTES:
            index_path = os.path.join(project_root, "index.html")
            if os.path.exists(index_path):
                return FileResponse(index_path)
        raise HTTPException(status_code=404, detail=f"Endpoint or page '/{page_route}' not found.")

    # Endpoint 1: Open-Meteo Weather API
    @app.get("/api/v2/climate/weather")
    def get_weather_telemetry(
        lat: float = Query(21.1458, description="Latitude in decimal degrees"),
        lng: float = Query(79.0882, description="Longitude in decimal degrees"),
        start_date: Optional[str] = Query(None, description="Start date YYYY-MM-DD"),
        end_date: Optional[str] = Query(None, description="End date YYYY-MM-DD")
    ):
        result = weather_service.fetch_weather_telemetry(lat, lng, start_date, end_date)
        if result.get("status") == "ERROR":
            raise HTTPException(status_code=400, detail=result.get("error"))
        return result

    # Endpoint 2: NASA / USGS Landsat-8 & 9 30m Satellite Telemetry API
    @app.get("/api/v2/climate/satellite")
    def get_satellite_telemetry(
        lat: float = Query(21.1458, description="Latitude in decimal degrees"),
        lng: float = Query(79.0882, description="Longitude in decimal degrees"),
        start_date: Optional[str] = Query(None, description="Start date YYYY-MM-DD"),
        end_date: Optional[str] = Query(None, description="End date YYYY-MM-DD")
    ):
        result = sentinel_service.fetch_satellite_telemetry(lat, lng, start_date, end_date)
        if result.get("status") == "ERROR":
            raise HTTPException(status_code=400, detail=result.get("error"))
        return result

    # Endpoint 3: ISRIC SoilGrids REST API v2.0
    @app.get("/api/v2/climate/soil")
    def get_soil_telemetry(
        lat: float = Query(21.1458, description="Latitude in decimal degrees"),
        lng: float = Query(79.0882, description="Longitude in decimal degrees")
    ):
        result = soil_service.fetch_soil_properties(lat, lng)
        if result.get("status") == "ERROR":
            raise HTTPException(status_code=400, detail=result.get("error"))
        return result

    # Endpoint 4: Unified Environmental Telemetry Pipeline
    @app.get("/api/v2/climate/telemetry")
    def get_unified_telemetry(
        lat: float = Query(21.1458, description="Latitude in decimal degrees"),
        lng: float = Query(79.0882, description="Longitude in decimal degrees"),
        start_date: Optional[str] = Query(None, description="Start date YYYY-MM-DD"),
        end_date: Optional[str] = Query(None, description="End date YYYY-MM-DD")
    ):
        weather = weather_service.fetch_weather_telemetry(lat, lng, start_date, end_date)
        satellite = sentinel_service.fetch_satellite_telemetry(lat, lng, start_date, end_date)
        soil = soil_service.fetch_soil_properties(lat, lng)

        return {
            "status": "SUCCESS",
            "lat": lat,
            "lng": lng,
            "queryTimestamp": datetime.datetime.now().isoformat(),
            "weather": weather,
            "satellite": satellite,
            "soil": soil
        }

if __name__ == "__main__":
    import uvicorn
    print("[NABARD Backend] Launching Phase 2 Telemetry Server on http://localhost:8000 ...")
    uvicorn.run(app, host="0.0.0.0", port=8000)
