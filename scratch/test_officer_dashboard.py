import os
import sys
import json

# Ensure project root is in python path
sys.path.insert(0, os.path.abspath("."))

from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

def run_officer_dashboard_tests():
    print("=== 1. Testing Officer Login & Authentication ===")
    login_resp = client.post("/api/v2/auth/login", json={
        "username": "officer1",
        "password": "officer123",
        "login_type": "officer"
    })
    assert login_resp.status_code == 200, f"Officer login failed: {login_resp.text}"
    token_data = login_resp.json()
    token = token_data["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    print(f"[OK] Bank Officer logged in as: {token_data['user']['full_name']} ({token_data['user']['sub']})")

    print("\n=== 2. Testing /api/v2/officer/dashboard-summary ===")
    summary_resp = client.get("/api/v2/officer/dashboard-summary", headers=headers)
    assert summary_resp.status_code == 200, f"Summary failed: {summary_resp.text}"
    s_data = summary_resp.json()
    assert "summary" in s_data
    summary = s_data["summary"]
    assert summary["total_applications"] >= 100
    assert "risk_level_distribution" in s_data
    assert "climate_risk_trends" in s_data
    print(f"[OK] Summary retrieved! Total Apps: {summary['total_applications']} | Awaiting Review: {summary['awaiting_review_count']}")
    print(f"     Risk Distribution: {s_data['risk_level_distribution']}")

    print("\n=== 3. Testing /api/v2/officer/applications Search & Filter Queue ===")
    # Queue all
    q_all_resp = client.get("/api/v2/officer/applications", headers=headers)
    assert q_all_resp.status_code == 200
    all_apps = q_all_resp.json()["applications"]
    assert len(all_apps) >= 100
    print(f"[OK] Full Queue retrieved: {len(all_apps)} applications listed.")

    # Search filter
    q_search_resp = client.get("/api/v2/officer/applications?search=DEMO001", headers=headers)
    assert q_search_resp.status_code == 200
    searched = q_search_resp.json()["applications"]
    assert len(searched) > 0
    assert searched[0]["farmer_id"] == "DEMO001"
    print(f"[OK] Search query 'DEMO001' returned {len(searched)} matching record(s).")

    print("\n=== 4. Testing /api/v2/officer/applications/{id} 10-Section Comprehensive Review File ===")
    detail_resp = client.get("/api/v2/officer/applications/DEMO001", headers=headers)
    assert detail_resp.status_code == 200, f"Detail failed: {detail_resp.text}"
    file_data = detail_resp.json()

    assert "section_1_farmer_profile" in file_data
    assert "section_2_bank_and_financials" in file_data
    assert "section_3_credit_score_repayment" in file_data
    assert "section_4_existing_obligations" in file_data
    assert "section_5_climate_weather_analysis" in file_data
    assert "section_6_satellite_agronomic" in file_data
    assert "section_7_risk_assessment_repayment_prob" in file_data
    assert "section_8_risk_drivers_explanation" in file_data
    assert "section_9_missing_data_warnings" in file_data
    assert "section_10_audit_trail_history" in file_data

    # Verify unmasked officer bank view
    acct = file_data["section_2_bank_and_financials"]["kcc_account_number"]
    assert "RESTRICTED" not in acct
    print(f"[OK] All 10 Application Review File sections present cleanly! Unmasked KCC Acct: {acct}")

    print("\n=== 5. Testing Officer Decision Rationale Validation ===")
    # Approve without rationale should be rejected with 400
    invalid_action = client.post("/api/v2/officer/applications/DEMO001/status", headers=headers, json={
        "action": "approve",
        "explanation_or_notes": "" # Missing mandatory rationale!
    })
    assert invalid_action.status_code == 400, f"Expected 400 for missing explanation rationale, got {invalid_action.status_code}"
    print("[OK] Rationale validation passed: Rejecting action without explanation with HTTP 400.")

    print("\n=== 6. Testing Valid Officer Status Transition & Audit Trail ===")
    valid_action = client.post("/api/v2/officer/applications/DEMO001/status", headers=headers, json={
        "action": "approve",
        "explanation_or_notes": "Approved based on solid CIBIL score (740), verified land record, and mandatory PMFBY weather insurance.",
        "approved_amount_inr": 180000.0
    })
    assert valid_action.status_code == 200, f"Valid action failed: {valid_action.text}"
    act_data = valid_action.json()
    assert act_data["new_status"] == "Approved"
    assert "audit_entry" in act_data
    print(f"[OK] Decision recorded! Application DEMO001 status updated to: {act_data['new_status']}")

    # Verify audit log in detail endpoint
    detail_resp2 = client.get("/api/v2/officer/applications/DEMO001", headers=headers)
    audit_history = detail_resp2.json()["section_10_audit_trail_history"]
    latest_audit = next((a for a in audit_history if a.get("action") in ("approve", "Approved")), None)
    assert latest_audit is not None, "Latest decision audit record not found in application review file!"
    print(f"[OK] Audit log verified in Section 10 timeline for officer: {latest_audit.get('officer_name', latest_audit.get('officer_username'))}")

    print("\n=== ALL BANK OFFICER DASHBOARD & REVIEW WORKFLOW TESTS PASSED! ===")

if __name__ == "__main__":
    run_officer_dashboard_tests()
