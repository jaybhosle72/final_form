import os
import sys
import json

# Add project root to sys.path
sys.path.insert(0, os.path.abspath("."))

from fastapi.testclient import TestClient
from backend.main import app
from backend.analytics.risk_engine import ClimateCreditRiskEngine

client = TestClient(app)
engine = ClimateCreditRiskEngine()

def run_all_risk_engine_tests():
    print("=== 1. Testing Missing Data & Fallbacks ===")
    minimal_app = {"applicantName": "Minimal Test Farmer", "loanAmount": 150000}
    res_minimal = engine.assess_risk(app_data=minimal_app, yield_data={}, weather_data={})
    assert res_minimal["overall_risk_classification"] in ("Low", "Moderate", "High")
    assert res_minimal["probability_model_status"] == "PROTOTYPE_RISK_SCORE"
    assert "PROTOTYPE RISK SCORE" in res_minimal["calibration_label"]
    print("[OK] Minimal inputs processed gracefully without exception.")

    print("\n=== 2. Testing Extreme Climate Inputs ===")
    # Extreme Drought
    drought_weather = {"avgTemperatureC": 36.5, "rainfallDeficitPct": -55.0, "heatwaveDays": 6, "soilMoistureIndex": 0.18}
    res_drought = engine.assess_risk(app_data={"irrigationType": "Rainfed", "cibilScore": 750}, yield_data={"predictedYieldTonsPerHa": 1.2}, weather_data=drought_weather)
    assert res_drought["climate_risk_classification"] == "High"
    print(f"[OK] Severe Drought test passed: Climate Risk = {res_drought['climate_risk_classification']} | Score = {res_drought['climate_risk_score_raw']}")

    # Heavy Flood
    flood_weather = {"avgTemperatureC": 26.0, "rainfallDeficitPct": 75.0, "heatwaveDays": 0, "soilMoistureIndex": 0.95}
    res_flood = engine.assess_risk(app_data={"irrigationType": "Rainfed"}, yield_data={"predictedYieldTonsPerHa": 2.0}, weather_data=flood_weather)
    assert res_flood["climate_risk_classification"] in ("Moderate", "High")
    print(f"[OK] Flood Anomaly test passed: Climate Risk = {res_flood['climate_risk_classification']}")

    print("\n=== 3. Testing Inconsistent Inputs (High CIBIL vs Low DSCR / High Climate Risk) ===")
    inconsistent_app = {
        "applicantName": "Inconsistent Borrower",
        "cibilScore": 820,
        "loanAmount": 2000000, # Large loan
        "tenureMonths": 12,
        "interestRate": 12.0,
        "irrigationType": "Rainfed",
        "existingObligations": 500000
    }
    res_inconsistent = engine.assess_risk(
        app_data=inconsistent_app,
        yield_data={"predictedYieldTonsPerHa": 1.5},
        weather_data={"avgTemperatureC": 35.0, "rainfallDeficitPct": -45.0, "heatwaveDays": 5}
    )
    # High CIBIL should NOT erase High Climate Risk or low DSCR!
    assert res_inconsistent["climate_risk_classification"] == "High"
    assert res_inconsistent["overall_risk_classification"] in ("Moderate", "High")
    print(f"[OK] Inconsistent input rule passed: High CIBIL (820) under extreme climate risk yields Overall Risk = {res_inconsistent['overall_risk_classification']}")

    print("\n=== 4. Testing API /api/v2/risk/assess & Assessment Persistence ===")
    login_resp = client.post("/api/v2/auth/login", json={"username": "officer1", "password": "officer123", "login_type": "officer"})
    assert login_resp.status_code == 200
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    assess_payload = {
        "farmer_id": "DEMO001",
        "district": "Pune",
        "state": "Maharashtra",
        "crop_type": "Pulses",
        "land_acres": 5.66,
        "loan_amount": 182000,
        "loan_term_months": 12,
        "interest_rate": 9.5,
        "irrigation_type": "Rainfed"
    }

    assess_api_resp = client.post("/api/v2/risk/assess", json=assess_payload, headers=headers)
    assert assess_api_resp.status_code == 200, f"API assess failed: {assess_api_resp.text}"
    data = assess_api_resp.json()
    assert data["status"] == "success"
    assert "assessment_id" in data
    assert data["risk_assessment"]["probability_model_status"] == "PROTOTYPE_RISK_SCORE"
    print(f"[OK] Risk API /assess passed. Assessment ID: {data['assessment_id']} | Model: {data['model_version']}")

    # Retrieve Saved Assessment
    get_resp = client.get(f"/api/v2/risk/assessments/DEMO001", headers=headers)
    assert get_resp.status_code == 200
    saved = get_resp.json()["assessment"]
    assert saved is not None
    assert saved["farmer_id"] == "DEMO001"
    assert saved["probability_model_status"] == "PROTOTYPE_RISK_SCORE"
    print(f"[OK] Saved assessment successfully retrieved for DEMO001!")

    print("\n=== ALL RISK ENGINE TESTS PASSED CLEANLY! ===")

if __name__ == "__main__":
    run_all_risk_engine_tests()
