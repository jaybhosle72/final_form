import os
import sys
import json

# Ensure project root is in python path
sys.path.insert(0, os.path.abspath("."))

from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

def run_end_to_end_scenario():
    print("==========================================================================")
    print("  END-TO-END QUALITY REVIEW & SCENARIO VERIFICATION")
    print("==========================================================================")

    # 1. Demo Farmer Login
    print("\n[Step 1] Demo Farmer ('farmer1') logging in...")
    resp1 = client.post("/api/v2/auth/login", json={
        "username": "farmer1",
        "password": "farmer123",
        "login_type": "farmer"
    })
    assert resp1.status_code == 200, f"Farmer login failed: {resp1.text}"
    farmer_token = resp1.json()["access_token"]
    farmer_headers = {"Authorization": f"Bearer {farmer_token}"}
    print(" -> [OK] Farmer logged in successfully. JWT Token acquired.")

    # 2. Farmer Dashboard & Linked Financial Info Retrieval
    print("\n[Step 2] Retrieving Farmer Profile, Financials, and Prefill Data...")
    dash_resp = client.get("/api/v2/farmers/me/dashboard", headers=farmer_headers)
    assert dash_resp.status_code == 200, f"Farmer dashboard failed: {dash_resp.text}"
    dash_data = dash_resp.json()
    assert "profile" in dash_data
    assert "bank_summary" in dash_data
    assert "credit_summary" in dash_data
    print(f" -> [OK] Dashboard retrieved for farmer: {dash_data['authenticated_user']['full_name']}")
    print(f"        Linked CIBIL Credit Summary: {dash_data['credit_summary']}")
    print(f"        Masked KCC Acct Number: {dash_data['bank_summary'].get('account_number_masked')}")

    prefill_resp = client.get("/api/v2/farmers/me/application-prefill", headers=farmer_headers)
    assert prefill_resp.status_code == 200, f"Prefill failed: {prefill_resp.text}"
    prefill_data = prefill_resp.json()["prefilled"]
    print(f" -> [OK] Verified Prefill Data loaded: Crop={prefill_data.get('crop_type')}, Land={prefill_data.get('farm_area_acres')} acres")

    # 3. Farmer Submits Loan Application with Custom Inputs
    print("\n[Step 3] Submitting Loan Application with complete custom inputs...")
    loan_payload = {
        "farmer_id": dash_data["profile"].get("farmer_id", "DEMO001"),
        "applicant_name": dash_data["authenticated_user"].get("full_name", "Ramesh Patil"),
        "district": prefill_data.get("district", "Dharwad"),
        "state": prefill_data.get("state", "Karnataka"),
        "crop_type": prefill_data.get("crop_type", "Wheat"),
        "farm_area_acres": float(prefill_data.get("farm_area_acres", 5.0)),
        "estimated_annual_income": float(prefill_data.get("estimated_annual_income_inr", 350000.0)),
        "loan_amount_inr": 150000.0,
        "loan_term_months": 12,
        "loan_purpose": "Kharif Crop Production & Micro-Irrigation Upgrade",
        "irrigation_type": prefill_data.get("irrigation_type", "Drip Irrigation"),
        "water_source": prefill_data.get("water_source", "Borewell + Canal"),
        "soil_type": prefill_data.get("soil_type", "Black Alluvial Soil"),
        "sowing_date": "2026-06-15",
        "expected_harvest_date": "2026-10-30",
        "existing_loan_obligations_inr": 25000.0
    }
    sub_resp = client.post("/api/v2/risk/submit-loan", headers=farmer_headers, json=loan_payload)
    assert sub_resp.status_code in [200, 201], f"Loan submission failed: {sub_resp.text}"
    sub_data = sub_resp.json()
    app_id = sub_data.get("application_id")
    assert app_id and app_id.startswith("APP-2026-"), f"Invalid application ID generated: {app_id}"
    print(f" -> [OK] Loan Application Submitted! Assigned Unique Application ID: {app_id}")

    # 4. Bank Officer Login
    print("\n[Step 4] Bank Officer ('officer1') logging in...")
    resp_off = client.post("/api/v2/auth/login", json={
        "username": "officer1",
        "password": "officer123",
        "login_type": "officer"
    })
    assert resp_off.status_code == 200, f"Officer login failed: {resp_off.text}"
    off_token = resp_off.json()["access_token"]
    off_headers = {"Authorization": f"Bearer {off_token}"}
    print(" -> [OK] Bank Officer logged in. JWT Token acquired.")

    # 5. Officer Applications Queue Listing
    print("\n[Step 5] Officer retrieving Application Queue & locating new submission...")
    q_resp = client.get("/api/v2/officer/applications", headers=off_headers)
    assert q_resp.status_code == 200, f"Officer queue failed: {q_resp.text}"
    apps_list = q_resp.json()["applications"]
    found_app = next((a for a in apps_list if a.get("application_id") == app_id), None)
    assert found_app is not None, f"Submitted application {app_id} not found in officer queue!"
    print(f" -> [OK] Application {app_id} located in Officer Queue! Status: {found_app.get('current_status')}")

    # 6. Officer Opens 10-Section Comprehensive Review File
    print("\n[Step 6] Officer opening 10-Section Application Review File for ID: " + app_id + "...")
    file_resp = client.get(f"/api/v2/officer/applications/{app_id}", headers=off_headers)
    assert file_resp.status_code == 200, f"Failed to retrieve application file: {file_resp.text}"
    file_data = file_resp.json()
    
    sections = [
        "section_1_farmer_profile",
        "section_2_bank_and_financials",
        "section_3_credit_score_repayment",
        "section_4_existing_obligations",
        "section_5_climate_weather_analysis",
        "section_6_satellite_agronomic",
        "section_7_risk_assessment_repayment_prob",
        "section_8_risk_drivers_explanation",
        "section_9_missing_data_warnings",
        "section_10_audit_trail_history"
    ]
    for sec in sections:
        assert sec in file_data, f"Missing section in file: {sec}"
    print(" -> [OK] All 10 mandatory sections present in Bank Officer Review File.")

    # 7. Dual-Pillar Risk Engine Assessment Verification inside Review File
    print("\n[Step 7] Verifying Automatic Dual-Pillar Risk Assessment Calculation...")
    sec7 = file_data["section_7_risk_assessment_repayment_prob"]
    assert "overall_risk_classification" in sec7 or "overall_risk_level" in sec7
    assert "probability_model_status" in sec7 or "calibration_status" in sec7
    status_label = sec7.get("probability_model_status") or sec7.get("calibration_status")
    assert status_label == "PROTOTYPE_RISK_SCORE"
    print(f" -> [OK] Dual-Pillar Risk Scores generated:")
    print(f"        Overall Risk: {sec7.get('overall_risk_classification')} | Probability Status: {status_label}")
    print(f"        Climate Risk: {sec7.get('climate_risk_classification')} | Financial Risk: {sec7.get('financial_risk_classification')}")

    # 8. Review Drivers, Provenance & Warnings
    print("\n[Step 8] Verifying Risk Drivers, Provenance & Missing-Data Warnings...")
    sec8 = file_data["section_8_risk_drivers_explanation"]
    sec9 = file_data["section_9_missing_data_warnings"]
    pos_factors = sec8.get("positive_factors") or sec8.get("positive_drivers", [])
    neg_factors = sec8.get("negative_factors") or sec8.get("negative_drivers", [])
    assert pos_factors is not None and neg_factors is not None
    assert sec9 is not None
    print(f" -> [OK] Drivers verified: {len(pos_factors)} positive, {len(neg_factors)} negative.")
    print(f"        Missing-data warnings tracked cleanly: {len(sec9)} warning item(s).")

    # 9. Officer Decision Rationale Validation (Rejection on missing explanation)
    print("\n[Step 9] Testing Officer Decision Rationale Validation (empty explanation rejection)...")
    inv_dec = client.post(f"/api/v2/officer/applications/{app_id}/status", headers=off_headers, json={
        "action": "approve",
        "explanation_or_notes": ""
    })
    assert inv_dec.status_code == 400, f"Expected HTTP 400 for empty explanation, got {inv_dec.status_code}"
    print(" -> [OK] Rationale validation passed: Decision without explanation rejected with HTTP 400.")

    # 10. Officer Records Lending Decision
    print("\n[Step 10] Officer recording lending decision 'Approved' with detailed rationale...")
    dec_resp = client.post(f"/api/v2/officer/applications/{app_id}/status", headers=off_headers, json={
        "action": "approve",
        "explanation_or_notes": "Approved following automated dual-pillar risk assessment. Strong CIBIL history, verified land record, and low climate vulnerability.",
        "approved_amount_inr": 150000.0
    })
    assert dec_resp.status_code == 200, f"Decision recording failed: {dec_resp.text}"
    dec_data = dec_resp.json()
    assert dec_data["new_status"] == "Approved"
    print(f" -> [OK] Decision successfully recorded! Application {app_id} status updated to: Approved.")

    # 11. Farmer Checks Status & Verifies Update
    print("\n[Step 11] Farmer re-checking Dashboard status...")
    dash_resp2 = client.get("/api/v2/farmers/me/dashboard", headers=farmer_headers)
    assert dash_resp2.status_code == 200
    farmer_apps = dash_resp2.json()["applications"]
    updated_app = next((a for a in farmer_apps if a.get("application_id") == app_id or a.get("loan_id") == app_id), None)
    assert updated_app is not None, f"Application {app_id} not found in farmer dashboard!"
    assert updated_app.get("status") in ["Approved", "approved"], f"Status mismatch: {updated_app.get('status')}"
    print(f" -> [OK] Farmer Dashboard accurately reflects updated status: {updated_app.get('status')}")

    # 12. Persistence Verification Across Re-fetches
    print("\n[Step 12] Verifying Audit Trail Persistence across re-fetches...")
    file_resp2 = client.get(f"/api/v2/officer/applications/{app_id}", headers=off_headers)
    audit_trail = file_resp2.json()["section_10_audit_trail_history"]
    assert len(audit_trail) > 0, "Audit trail empty!"
    latest = audit_trail[-1]
    assert latest.get("new_status") in ["Approved", "approved"] or latest.get("action") in ["approve", "Approved", "APPROVE"]
    print(f" -> [OK] Audit entry persisted in history with timestamp: {latest.get('timestamp')}")

    # 13. Security & RBAC Enforcement Checks
    print("\n[Step 13] Performing Security Audit & RBAC Enforcement Verification...")
    
    # 13a. Farmer attempting Officer endpoint access (Must fail with HTTP 403)
    rbac_resp1 = client.get("/api/v2/officer/dashboard-summary", headers=farmer_headers)
    assert rbac_resp1.status_code == 403, f"Expected 403 for farmer accessing officer summary, got {rbac_resp1.status_code}"
    
    rbac_resp2 = client.post(f"/api/v2/officer/applications/{app_id}/status", headers=farmer_headers, json={
        "action": "approve",
        "explanation_or_notes": "Malicious attempt to self-approve loan."
    })
    assert rbac_resp2.status_code == 403, f"Expected 403 for farmer attempting decision action, got {rbac_resp2.status_code}"
    print(" -> [OK] RBAC 403 Enforcement verified: Farmers strictly blocked from officer endpoints.")

    # 13b. Cross-Farmer Privacy Isolation Check
    resp_f2 = client.post("/api/v2/auth/login", json={
        "username": "farmer2",
        "password": "farmer123",
        "login_type": "farmer"
    })
    assert resp_f2.status_code == 200
    f2_token = resp_f2.json()["access_token"]
    f2_headers = {"Authorization": f"Bearer {f2_token}"}
    
    # farmer2 attempting to view farmer1's profile directly
    priv_resp = client.get("/api/v2/farmers/DEMO001/profile", headers=f2_headers)
    assert priv_resp.status_code in [403, 401], f"Expected 403/401 for farmer2 accessing farmer1's profile, got {priv_resp.status_code}"
    print(" -> [OK] Cross-Farmer Privacy Isolation verified: Farmer2 cannot access Farmer1's private records.")

    print("\n==========================================================================")
    print("  ALL 13 END-TO-END QUALITY SCENARIOS & SECURITY CHECKS PASSED SUCCESSFULLY!")
    print("==========================================================================")

if __name__ == "__main__":
    run_end_to_end_scenario()
