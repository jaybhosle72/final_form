import os
import sys
import json

# Ensure project root is in python path
sys.path.insert(0, os.path.abspath("."))

from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

def test_google_authentication_flow():
    print("==========================================================================")
    print("  TESTING GOOGLE OAUTH 2.0 INTEGRATION & FALLBACK HANDLING")
    print("==========================================================================")

    # 1. Unconfigured Environment Checks
    print("\n[Step 1] Testing /api/v2/auth/google/config in unconfigured state...")
    # Temporarily clear env vars if present for test baseline
    old_cid = os.environ.pop("GOOGLE_CLIENT_ID", None)
    old_sec = os.environ.pop("GOOGLE_CLIENT_SECRET", None)

    cfg_resp = client.get("/api/v2/auth/google/config")
    assert cfg_resp.status_code == 200, f"Config check failed: {cfg_resp.text}"
    cfg_data = cfg_resp.json()
    assert cfg_data["status"] == "success"
    assert cfg_data["is_configured"] == False
    assert "GOOGLE_CLIENT_ID" in cfg_data["message"] or "not configured" in cfg_data["message"]
    print(f" -> [OK] Config endpoint returned is_configured=False as expected.")
    print(f"        Message: {cfg_data['message']}")

    # 2. Testing Authorization URL generation when unconfigured (Must yield 503)
    print("\n[Step 2] Testing /api/v2/auth/google/url when unconfigured...")
    url_resp = client.get("/api/v2/auth/google/url")
    assert url_resp.status_code == 503, f"Expected 503 for unconfigured Google Auth, got {url_resp.status_code}"
    err_detail = url_resp.json()["detail"]
    assert err_detail.get("code") == "OAUTH_NOT_CONFIGURED"
    print(f" -> [OK] Request safely rejected with HTTP 503 (code: {err_detail.get('code')}).")

    # 3. Testing Token submission when unconfigured (Must yield 503)
    print("\n[Step 3] Testing /api/v2/auth/google/token when unconfigured...")
    tok_resp = client.post("/api/v2/auth/google/token", json={"code": "dummy_code_123"})
    assert tok_resp.status_code == 503, f"Expected 503 for unconfigured token exchange, got {tok_resp.status_code}"
    print(" -> [OK] Token exchange endpoint safely rejected with HTTP 503.")

    # 4. Simulating Configured Google OAuth Environment
    print("\n[Step 4] Simulating configured Google OAuth environment variables...")
    os.environ["GOOGLE_CLIENT_ID"] = "1234567890-testclientid.apps.googleusercontent.com"
    os.environ["GOOGLE_CLIENT_SECRET"] = "GOCSPX-TestClientSecretKey2026"
    os.environ["GOOGLE_REDIRECT_URI"] = "http://localhost:8000/api/v2/auth/google/callback"
    os.environ["GOOGLE_OFFICER_EMAILS"] = "bank.officer.test@nabard.in,officer1@bank.org"

    cfg_resp2 = client.get("/api/v2/auth/google/config")
    assert cfg_resp2.status_code == 200
    assert cfg_resp2.json()["is_configured"] == True
    assert cfg_resp2.json()["client_id"] == os.environ["GOOGLE_CLIENT_ID"]
    print(" -> [OK] Config endpoint now reports is_configured=True.")

    # 5. Testing Authorization URL generation when configured
    print("\n[Step 5] Testing /api/v2/auth/google/url when configured...")
    url_resp2 = client.get("/api/v2/auth/google/url")
    assert url_resp2.status_code == 200, f"URL generation failed: {url_resp2.text}"
    auth_url = url_resp2.json()["authorization_url"]
    assert "accounts.google.com" in auth_url
    assert "1234567890-testclientid" in auth_url
    print(f" -> [OK] Official Google OAuth URL generated successfully:")
    print(f"        URL: {auth_url[:75]}...")

    # Restore old environment if it existed
    if old_cid:
        os.environ["GOOGLE_CLIENT_ID"] = old_cid
    else:
        os.environ.pop("GOOGLE_CLIENT_ID", None)
    if old_sec:
        os.environ["GOOGLE_CLIENT_SECRET"] = old_sec
    else:
        os.environ.pop("GOOGLE_CLIENT_SECRET", None)

    print("\n==========================================================================")
    print("  GOOGLE OAUTH 2.0 INTEGRATION & FALLBACK TESTS PASSED 100%!")
    print("==========================================================================")

if __name__ == "__main__":
    test_google_authentication_flow()
