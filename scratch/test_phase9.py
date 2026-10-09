import os
import sys

# Ensure backend directory is in python path
sys.path.insert(0, os.path.abspath("."))

from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

def test_farmer_dashboard_and_loan_flow():
    print("--- 1. Testing Farmer Login ---")
    login_resp = client.post("/api/v2/auth/login", json={
        "username": "farmer1",
        "password": "farmer123",
        "login_type": "farmer"
    })
    assert login_resp.status_code == 200, f"Login failed: {login_resp.text}"
    token_data = login_resp.json()
    token = token_data["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    print(f"[OK] Farmer logged in. Token acquired for farmer: {token_data['user']['farmer_id']}")

    print("\n--- 2. Testing /api/v2/farmers/me/dashboard ---")
    dash_resp = client.get("/api/v2/farmers/me/dashboard", headers=headers)
    assert dash_resp.status_code == 200, f"Dashboard failed: {dash_resp.text}"
    dash = dash_resp.json()
    assert dash["profile"]["farmer_id"] == "DEMO001"
    assert "bank_summary" in dash
    assert "credit_summary" in dash
    assert "applications" in dash
    print(f"[OK] Dashboard loaded successfully for {dash['authenticated_user']['full_name']}")
    print(f"   Bank Acct: {dash['bank_summary']['account_number_masked']} | CIBIL: {dash['credit_summary']['derived_cibil_score']}")

    print("\n--- 3. Testing /api/v2/farmers/me/application-prefill ---")
    prefill_resp = client.get("/api/v2/farmers/me/application-prefill", headers=headers)
    assert prefill_resp.status_code == 200, f"Prefill failed: {prefill_resp.text}"
    prefill = prefill_resp.json()["prefilled"]
    assert prefill["applicant_name"] != ""
    assert prefill["farm_area_acres"] > 0
    print(f"[OK] Application prefill fetched: {prefill['applicant_name']} ({prefill['farm_area_acres']} acres, {prefill['crop_type']})")

    print("\n--- 4. Testing Invalid Loan Application Validation ---")
    invalid_resp = client.post("/api/v2/risk/submit-loan", headers=headers, json={
        "applicant_name": "Test Farmer",
        "district": "Pune",
        "state": "Maharashtra",
        "crop_type": "Sugarcane",
        "farm_area_acres": 0, # INVALID
        "estimated_annual_income": 200000,
        "loan_amount_inr": 150000,
        "loan_term_months": 12,
        "loan_purpose": "Crop Input"
    })
    assert invalid_resp.status_code in (400, 422), f"Expected 400/422 for 0 acres, got {invalid_resp.status_code}"
    print("[OK] Validation check passed: Rejected 0 acres with HTTP 400/422.")

    print("\n--- 5. Testing Valid Loan Application Submission ---")
    valid_payload = {
        "applicant_name": prefill["applicant_name"],
        "phone_number": prefill["phone_number"],
        "village_taluka": "Khed",
        "district": prefill["district"],
        "state": prefill["state"],
        "crop_type": prefill["crop_type"],
        "farm_area_acres": prefill["farm_area_acres"],
        "sowing_date": "2026-06-15",
        "expected_harvest_date": "2026-11-20",
        "irrigation_type": prefill["irrigation_type"],
        "water_source": "Canal Irrigation",
        "soil_type": "Black Cotton Soil",
        "previous_crop_yield_tons_ha": 5.2,
        "estimated_annual_income": prefill["estimated_annual_income_inr"],
        "loan_amount_inr": 250000,
        "loan_term_months": 24,
        "loan_purpose": "Solar Irrigation Pump Setup",
        "repayment_source": "Harvest Cash Crops",
        "existing_loan_obligations_inr": 0,
        "land_document_status": "7/12 Verified"
    }
    submit_resp = client.post("/api/v2/risk/submit-loan", headers=headers, json=valid_payload)
    assert submit_resp.status_code == 200, f"Submit loan failed: {submit_resp.text}"
    submit_data = submit_resp.json()
    assert submit_data["application_status"] == "Submitted" or submit_data["status"] == "success"
    assert submit_data["application_id"].startswith("APP-2026-")
    print(f"[OK] Loan application submitted! ID: {submit_data['application_id']} | Status: {submit_data['application_status']}")

    print("\n--- 6. Verifying Dashboard Application Tracking ---")
    dash_resp2 = client.get("/api/v2/farmers/me/dashboard", headers=headers)
    assert dash_resp2.status_code == 200
    apps = dash_resp2.json()["applications"]
    created_app = next((a for a in apps if a["application_id"] == submit_data["application_id"]), None)
    assert created_app is not None, "Newly submitted application not found in farmer dashboard list!"
    assert created_app["status"] in ["Submitted", "Approved"]
    print(f"[OK] Application {submit_data['application_id']} correctly present in Farmer Dashboard application queue!")

if __name__ == "__main__":
    test_farmer_dashboard_and_loan_flow()
    print("\nALL PHASE 9 / FARMER DASHBOARD & LOAN APPLICATION TESTS PASSED!")
