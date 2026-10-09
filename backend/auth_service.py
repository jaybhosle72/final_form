import os
import json
import time
import base64
import hmac
import hashlib
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, HTTPException, Depends, Header, Request, Query
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
USERS_FILE = os.path.join(BASE_DIR, "data", "users.json")
SECRET_KEY = "NABARD_SECRET_KEY_CLIMATE_CREDIT_RISK_2026_PROD_DEMO"

router = APIRouter(prefix="/api/v2/auth", tags=["Authentication & Access Control"])

# Utility Functions for JWT & Password Hashing
def b64_url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("utf-8").rstrip("=")

def b64_url_decode(s: str) -> bytes:
    padding = "=" * ((4 - len(s) % 4) % 4)
    return base64.urlsafe_b64decode(s + padding)

def hash_password(password: str, salt: str = "nabard_salt_2026") -> str:
    return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 10000).hex()

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return hmac.compare_digest(hash_password(plain_password), hashed_password)

def create_access_token(payload: Dict[str, Any], expires_in: int = 86400) -> str:
    header = {"alg": "HS256", "typ": "JWT"}
    payload_copy = payload.copy()
    payload_copy["exp"] = int(time.time()) + expires_in
    payload_copy["iat"] = int(time.time())

    h_b64 = b64_url_encode(json.dumps(header).encode("utf-8"))
    p_b64 = b64_url_encode(json.dumps(payload_copy).encode("utf-8"))
    
    signing_input = f"{h_b64}.{p_b64}".encode("utf-8")
    signature = hmac.new(SECRET_KEY.encode("utf-8"), signing_input, hashlib.sha256).digest()
    sig_b64 = b64_url_encode(signature)

    return f"{h_b64}.{p_b64}.{sig_b64}"

def decode_access_token(token: str) -> Dict[str, Any]:
    try:
        parts = token.split(".")
        if len(parts) != 3:
            raise ValueError("Invalid token structure.")
        
        h_b64, p_b64, sig_b64 = parts
        signing_input = f"{h_b64}.{p_b64}".encode("utf-8")
        expected_sig = hmac.new(SECRET_KEY.encode("utf-8"), signing_input, hashlib.sha256).digest()
        actual_sig = b64_url_decode(sig_b64)

        if not hmac.compare_digest(expected_sig, actual_sig):
            raise ValueError("Token signature verification failed.")

        payload = json.loads(b64_url_decode(p_b64).decode("utf-8"))
        if payload.get("exp") and time.time() > payload["exp"]:
            raise ValueError("Token has expired.")

        return payload
    except Exception as e:
        raise HTTPException(status_code=401, detail={
            "status": "error",
            "message": f"Authentication failed: {str(e)}",
            "code": "INVALID_TOKEN"
        })

# User Data Persistence Helpers
def load_users() -> List[Dict[str, Any]]:
    if os.path.exists(USERS_FILE):
        try:
            with open(USERS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return []

def save_users(users: List[Dict[str, Any]]):
    os.makedirs(os.path.dirname(USERS_FILE), exist_ok=True)
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, indent=2)

def find_user_by_username(username: str) -> Optional[Dict[str, Any]]:
    users = load_users()
    u_norm = username.strip().lower()
    for u in users:
        if u.get("username", "").lower() == u_norm:
            return u
    return None

# Dependency Wrappers
def extract_token_from_request(request: Request) -> Optional[str]:
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        return auth_header[7:].strip()
    
    # Fallback headers / query
    token = request.headers.get("X-Access-Token") or request.query_params.get("token")
    return token

def get_current_user(request: Request) -> Dict[str, Any]:
    token = extract_token_from_request(request)
    if not token:
        raise HTTPException(status_code=401, detail={
            "status": "error",
            "message": "Authentication token missing. Please log in first.",
            "code": "AUTH_REQUIRED"
        })
    return decode_access_token(token)

def get_optional_user(request: Request) -> Optional[Dict[str, Any]]:
    token = extract_token_from_request(request)
    if not token:
        return None
    try:
        return decode_access_token(token)
    except Exception:
        return None

def require_role(allowed_roles: List[str]):
    def role_checker(current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
        user_role = current_user.get("role", "").lower().strip()
        allowed_norm = [r.lower().strip() for r in allowed_roles]
        
        if user_role not in allowed_norm:
            raise HTTPException(status_code=403, detail={
                "status": "error",
                "message": f"Forbidden. Role '{user_role}' is not authorized to access this resource. Required roles: {allowed_roles}",
                "code": "ROLE_FORBIDDEN"
            })
        return current_user
    return role_checker

def verify_farmer_ownership(requested_farmer_id: str, current_user: Dict[str, Any]):
    """Ensures a farmer can ONLY access their own farmer record."""
    role = current_user.get("role", "").lower().strip()
    if role in ["bank_officer", "officer", "admin"]:
        return  # Bank officers have permission across all records

    user_farmer_id = current_user.get("farmer_id")
    if not user_farmer_id or user_farmer_id.upper() != requested_farmer_id.upper():
        raise HTTPException(status_code=403, detail={
            "status": "error",
            "message": f"Forbidden. You are authorized to access only your own farmer profile ('{user_farmer_id}'). Access to '{requested_farmer_id}' is denied.",
            "code": "FARMER_RECORD_UNAUTHORIZED"
        })

# Request Models
class LoginRequest(BaseModel):
    username: str
    password: str
    login_type: Optional[str] = "farmer"  # "farmer" or "officer"

class RegisterFarmerRequest(BaseModel):
    username: str
    password: str
    full_name: str
    district: Optional[str] = "Dharwad"
    state: Optional[str] = "Karnataka"
    phone: Optional[str] = "+91 98765 00000"

class RegisterOfficerRequest(BaseModel):
    username: str
    password: str
    full_name: str
    designation: Optional[str] = "Credit Officer"
    branch: Optional[str] = "NABARD / Regional Rural Bank"
    invite_code: Optional[str] = None

# Endpoints
@router.post("/login")
def login(payload: LoginRequest):
    """Logs in a Farmer or Bank Officer and returns a signed JWT Token."""
    user = find_user_by_username(payload.username)
    if not user or not verify_password(payload.password, user.get("password_hash", "")):
        raise HTTPException(status_code=401, detail={
            "status": "error",
            "message": "Invalid username or password.",
            "code": "INVALID_CREDENTIALS"
        })

    user_role = user.get("role", "farmer")
    
    # Check login_type request alignment
    if payload.login_type and payload.login_type.lower() == "officer" and user_role != "bank_officer":
        raise HTTPException(status_code=403, detail={
            "status": "error",
            "message": "Account is a Farmer account. Please use the Farmer login portal.",
            "code": "ROLE_MISMATCH"
        })
    elif payload.login_type and payload.login_type.lower() == "farmer" and user_role == "bank_officer":
        raise HTTPException(status_code=403, detail={
            "status": "error",
            "message": "Account is a Bank Officer account. Please use the Officer portal login.",
            "code": "ROLE_MISMATCH"
        })

    token_payload = {
        "sub": user["username"],
        "role": user_role,
        "full_name": user.get("full_name"),
        "farmer_id": user.get("farmer_id"),
        "officer_id": user.get("officer_id")
    }

    token = create_access_token(token_payload)

    return {
        "status": "success",
        "message": f"Welcome back, {user.get('full_name')}!",
        "access_token": token,
        "token_type": "bearer",
        "user": token_payload
    }

@router.post("/register")
def register_farmer(payload: RegisterFarmerRequest):
    """Registers a new Farmer account. NEVER permits registering Bank Officer role."""
    if len(payload.username.strip()) < 3:
        raise HTTPException(status_code=400, detail={"status": "error", "message": "Username must be at least 3 characters long.", "code": "INVALID_USERNAME"})
    if len(payload.password.strip()) < 6:
        raise HTTPException(status_code=400, detail={"status": "error", "message": "Password must be at least 6 characters long.", "code": "INVALID_PASSWORD"})

    existing = find_user_by_username(payload.username)
    if existing:
        raise HTTPException(status_code=400, detail={"status": "error", "message": f"Username '{payload.username}' is already registered.", "code": "USERNAME_EXISTS"})

    users = load_users()
    new_farmer_num = 101 + len(users)
    new_farmer_id = f"DEMO{new_farmer_num:03d}"

    new_user = {
        "username": payload.username.strip(),
        "password_hash": hash_password(payload.password.strip()),
        "role": "farmer",  # Hardcoded role: farmer ONLY
        "farmer_id": new_farmer_id,
        "full_name": payload.full_name.strip(),
        "district": payload.district.strip(),
        "state": payload.state.strip(),
        "phone": payload.phone.strip()
    }

    users.append(new_user)
    save_users(users)

    token_payload = {
        "sub": new_user["username"],
        "role": "farmer",
        "full_name": new_user["full_name"],
        "farmer_id": new_farmer_id
    }
    token = create_access_token(token_payload)

    return {
        "status": "success",
        "message": "Farmer account registered successfully.",
        "access_token": token,
        "token_type": "bearer",
        "user": token_payload
    }

@router.post("/register-officer")
def register_officer(payload: RegisterOfficerRequest):
    """Registers a new Bank Officer account with administrative invite code verification."""
    valid_invite_codes = ["OFFICER_2026_ADMIN", "NABARD_OFFICER_INVITE", "ADMIN_SECRET"]
    code = (payload.invite_code or "").strip().upper()
    if code not in valid_invite_codes:
        raise HTTPException(status_code=403, detail={
            "status": "error",
            "message": "Invalid or missing Officer Authorization Invite Code. Bank officer registration requires administrative authorization.",
            "code": "INVALID_OFFICER_INVITE_CODE"
        })

    if len(payload.username.strip()) < 3:
        raise HTTPException(status_code=400, detail={"status": "error", "message": "Username must be at least 3 characters long.", "code": "INVALID_USERNAME"})
    if len(payload.password.strip()) < 6:
        raise HTTPException(status_code=400, detail={"status": "error", "message": "Password must be at least 6 characters long.", "code": "INVALID_PASSWORD"})

    existing = find_user_by_username(payload.username)
    if existing:
        raise HTTPException(status_code=400, detail={"status": "error", "message": f"Username '{payload.username}' is already registered.", "code": "USERNAME_EXISTS"})

    users = load_users()
    officer_count = sum(1 for u in users if u.get("role") == "bank_officer") + 1
    officer_id = f"OFFICER_{officer_count:03d}"

    new_user = {
        "username": payload.username.strip(),
        "password_hash": hash_password(payload.password.strip()),
        "role": "bank_officer",
        "officer_id": officer_id,
        "full_name": payload.full_name.strip(),
        "designation": payload.designation.strip() if payload.designation else "Credit Officer",
        "branch": payload.branch.strip() if payload.branch else "NABARD Regional Office"
    }

    users.append(new_user)
    save_users(users)

    token_payload = {
        "sub": new_user["username"],
        "role": "bank_officer",
        "full_name": new_user["full_name"],
        "officer_id": officer_id
    }
    token = create_access_token(token_payload)

    return {
        "status": "success",
        "message": "Bank Officer account registered successfully.",
        "access_token": token,
        "token_type": "bearer",
        "user": token_payload
    }

# Load environment variables from .env file if present
def load_env_file():
    env_paths = [
        os.path.join(os.getcwd(), ".env"),
        os.path.join(os.getcwd(), "backend", ".env"),
        os.path.join(BASE_DIR, ".env"),
        os.path.join(os.path.dirname(BASE_DIR), ".env"),
        os.path.join(os.path.dirname(os.path.dirname(BASE_DIR)), ".env")
    ]
    for env_path in env_paths:
        if os.path.exists(env_path):
            try:
                with open(env_path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#") and "=" in line:
                            k, v = line.split("=", 1)
                            k = k.strip()
                            v = v.strip().strip("'\"")
                            if k:
                                os.environ[k] = v
            except Exception:
                pass

load_env_file()

def is_google_auth_configured() -> bool:
    load_env_file()
    cid = os.getenv("GOOGLE_CLIENT_ID", "").strip()
    secret = os.getenv("GOOGLE_CLIENT_SECRET", "").strip()
    return bool(cid and secret and "your_google_client_id" not in cid.lower())

class GoogleAuthRequest(BaseModel):
    code: Optional[str] = None
    id_token: Optional[str] = None
    redirect_uri: Optional[str] = None

@router.get("/google/config")
def get_google_auth_config():
    """Returns Google OAuth availability status and configuration parameters."""
    configured = is_google_auth_configured()
    return {
        "status": "success",
        "is_configured": configured,
        "client_id": os.getenv("GOOGLE_CLIENT_ID") if configured else None,
        "redirect_uri": os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8000/api/v2/auth/google/callback"),
        "message": "Google OAuth is configured and ready." if configured else "Google OAuth credentials not configured in environment. Copy .env.example to .env and populate GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET."
    }

@router.get("/google/url")
def get_google_auth_url():
    """Generates official Google OAuth 2.0 authorization URL."""
    if not is_google_auth_configured():
        raise HTTPException(status_code=503, detail={
            "status": "error",
            "message": "Google OAuth is not configured. Please set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in .env file.",
            "code": "OAUTH_NOT_CONFIGURED"
        })
    client_id = os.getenv("GOOGLE_CLIENT_ID")
    redirect_uri = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8000/api/v2/auth/google/callback")
    scope = "openid email profile"
    import urllib.parse
    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": scope,
        "access_type": "offline",
        "prompt": "consent"
    }
    url = f"https://accounts.google.com/o/oauth2/v2/auth?{urllib.parse.urlencode(params)}"
    return {
        "status": "success",
        "authorization_url": url
    }

@router.get("/google/callback")
def google_auth_callback(code: Optional[str] = Query(None), error: Optional[str] = Query(None)):
    """Handles Google OAuth 2.0 Authorization Code callback redirect from Google servers."""
    if error or not code:
        err_msg = error or "Authorization code was not provided by Google."
        html_err = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Google Sign-In Failed</title>
    <style>
        body {{ font-family: system-ui, -apple-system, sans-serif; background: #0f172a; color: #f8fafc; display: flex; align-items: center; justify-content: center; height: 100vh; margin: 0; }}
        .box {{ background: #1e293b; border: 1px solid #334155; border-radius: 12px; padding: 2.5rem; text-align: center; max-width: 420px; box-shadow: 0 20px 25px -5px rgba(0,0,0,0.5); }}
        h2 {{ color: #ef4444; margin-top: 0; font-size: 1.5rem; }}
        p {{ color: #94a3b8; font-size: 0.95rem; line-height: 1.5; }}
        a {{ display: inline-block; margin-top: 1.5rem; background: #0d9488; color: #fff; text-decoration: none; padding: 0.75rem 1.5rem; border-radius: 8px; font-weight: 600; }}
        a:hover {{ background: #0f766e; }}
    </style>
</head>
<body>
    <div class="box">
        <h2>Authentication Failed</h2>
        <p>{err_msg}</p>
        <a href="/">Return to Main Portal</a>
    </div>
</body>
</html>"""
        return HTMLResponse(content=html_err, status_code=400)

    try:
        req_obj = GoogleAuthRequest(code=code)
        auth_result = authenticate_google_user(req_obj)
        auth_json = json.dumps(auth_result)
        
        html_success = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Authenticating with NABARD System...</title>
    <style>
        body {{ font-family: system-ui, -apple-system, sans-serif; background: #0f172a; color: #f8fafc; display: flex; align-items: center; justify-content: center; height: 100vh; margin: 0; }}
        .box {{ background: #1e293b; border: 1px solid #334155; border-radius: 12px; padding: 2.5rem; text-align: center; max-width: 420px; box-shadow: 0 20px 25px -5px rgba(0,0,0,0.5); }}
        .spinner {{ width: 44px; height: 44px; border: 4px solid #334155; border-top-color: #0d9488; border-radius: 50%; animation: spin 0.8s linear infinite; margin: 0 auto 1.5rem auto; }}
        @keyframes spin {{ to {{ transform: rotate(360deg); }} }}
        h3 {{ margin: 0 0 0.5rem 0; font-size: 1.25rem; color: #38bdf8; }}
        p {{ color: #94a3b8; font-size: 0.9rem; margin: 0; }}
    </style>
</head>
<body>
    <div class="box">
        <div class="spinner"></div>
        <h3>Google Authentication Successful</h3>
        <p>Signing in and loading your portal...</p>
    </div>
    <script id="auth-payload" type="application/json">
    {auth_json}
    </script>
    <script>
        (function() {{
            try {{
                const raw = document.getElementById('auth-payload').textContent;
                const data = JSON.parse(raw);
                if (data && data.access_token) {{
                    localStorage.setItem('NABARD_AUTH_SESSION', JSON.stringify(data));
                }}
            }} catch(e) {{
                console.error('Session storage error:', e);
            }}
            setTimeout(function() {{
                window.location.href = '/';
            }}, 300);
        }})();
    </script>
</body>
</html>"""
        return HTMLResponse(content=html_success)
    except Exception as e:
        err_detail = str(e)
        if isinstance(e, HTTPException) and isinstance(e.detail, dict):
            err_detail = e.detail.get("message", str(e.detail))
        html_err = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Authentication Error</title>
    <style>
        body {{ font-family: system-ui, -apple-system, sans-serif; background: #0f172a; color: #f8fafc; display: flex; align-items: center; justify-content: center; height: 100vh; margin: 0; }}
        .box {{ background: #1e293b; border: 1px solid #334155; border-radius: 12px; padding: 2.5rem; text-align: center; max-width: 420px; box-shadow: 0 20px 25px -5px rgba(0,0,0,0.5); }}
        h2 {{ color: #ef4444; margin-top: 0; font-size: 1.5rem; }}
        p {{ color: #94a3b8; font-size: 0.95rem; line-height: 1.5; }}
        a {{ display: inline-block; margin-top: 1.5rem; background: #0d9488; color: #fff; text-decoration: none; padding: 0.75rem 1.5rem; border-radius: 8px; font-weight: 600; }}
        a:hover {{ background: #0f766e; }}
    </style>
</head>
<body>
    <div class="box">
        <h2>Google Authentication Error</h2>
        <p>{err_detail}</p>
        <a href="/">Return to Main Portal</a>
    </div>
</body>
</html>"""
        return HTMLResponse(content=html_err, status_code=400)

@router.post("/google/token")
def authenticate_google_user(payload: GoogleAuthRequest):
    """Verifies Google OAuth Authorization Code or ID Token and returns an authenticated application JWT session."""
    if not is_google_auth_configured():
        raise HTTPException(status_code=503, detail={
            "status": "error",
            "message": "Google OAuth is not configured. Please set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in .env file.",
            "code": "OAUTH_NOT_CONFIGURED"
        })

    user_info = None
    import urllib.request, urllib.parse

    if payload.code:
        # Code Exchange Flow
        token_url = "https://oauth2.googleapis.com/token"
        req_data = urllib.parse.urlencode({
            "code": payload.code,
            "client_id": os.getenv("GOOGLE_CLIENT_ID"),
            "client_secret": os.getenv("GOOGLE_CLIENT_SECRET"),
            "redirect_uri": payload.redirect_uri or os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8000/api/v2/auth/google/callback"),
            "grant_type": "authorization_code"
        }).encode("utf-8")
        
        try:
            req = urllib.request.Request(token_url, data=req_data, headers={"Content-Type": "application/x-www-form-urlencoded"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                token_res = json.loads(resp.read().decode("utf-8"))
                access_tok = token_res.get("access_token")
                
                # Fetch User Profile via UserInfo
                userinfo_req = urllib.request.Request("https://www.googleapis.com/oauth2/v3/userinfo", headers={"Authorization": f"Bearer {access_tok}"})
                with urllib.request.urlopen(userinfo_req, timeout=10) as uresp:
                    user_info = json.loads(uresp.read().decode("utf-8"))
        except Exception as err:
            raise HTTPException(status_code=400, detail={
                "status": "error",
                "message": f"Failed to exchange Google OAuth authorization code: {str(err)}",
                "code": "GOOGLE_AUTH_FAILED"
            })

    elif payload.id_token:
        # ID Token Verification Flow
        tokeninfo_url = f"https://oauth2.googleapis.com/tokeninfo?id_token={payload.id_token}"
        try:
            req = urllib.request.Request(tokeninfo_url)
            with urllib.request.urlopen(req, timeout=10) as resp:
                user_info = json.loads(resp.read().decode("utf-8"))
                # Verify Audience matching GOOGLE_CLIENT_ID
                client_id = os.getenv("GOOGLE_CLIENT_ID")
                if user_info.get("aud") != client_id and user_info.get("azp") != client_id:
                    raise ValueError("ID Token audience mismatch.")
        except Exception as err:
            raise HTTPException(status_code=400, detail={
                "status": "error",
                "message": f"Failed to verify Google ID Token: {str(err)}",
                "code": "INVALID_GOOGLE_TOKEN"
            })
    else:
        raise HTTPException(status_code=400, detail={
            "status": "error",
            "message": "Either 'code' or 'id_token' is required for Google authentication.",
            "code": "MISSING_GOOGLE_CREDENTIALS"
        })

    if not user_info or "email" not in user_info:
        raise HTTPException(status_code=400, detail={"status": "error", "message": "Failed to retrieve valid email from Google authentication token.", "code": "GOOGLE_EMAIL_MISSING"})

    email = user_info["email"].lower().strip()
    google_sub = user_info.get("sub", email)
    full_name = user_info.get("name", email.split("@")[0].capitalize())

    # Server-Side Role Assignment Check: default to 'farmer', grant 'bank_officer' if email in allowlist
    officer_emails = [e.strip().lower() for e in os.getenv("GOOGLE_OFFICER_EMAILS", "").split(",") if e.strip()]
    allowlist_path = os.path.join(BASE_DIR, "data", "officer_allowlist.json")
    if os.path.exists(allowlist_path):
        try:
            with open(allowlist_path, "r", encoding="utf-8") as alf:
                allowed_list = json.load(alf)
                officer_emails.extend([a.lower().strip() for a in allowed_list])
        except Exception:
            pass

    is_officer = email in officer_emails
    user_role = "bank_officer" if is_officer else "farmer"

    # Update or persist user in data/users.json
    users = load_users()
    existing_user = None
    for u in users:
        if u.get("google_sub") == google_sub or u.get("email", "").lower() == email or u.get("username", "").lower() == email:
            existing_user = u
            break

    if existing_user:
        existing_user["full_name"] = full_name
        existing_user["role"] = user_role
        existing_user["google_sub"] = google_sub
        existing_user["email"] = email
        if user_role == "farmer" and not existing_user.get("farmer_id"):
            existing_user["farmer_id"] = f"DEMO{101 + len(users):03d}"
        elif user_role == "bank_officer" and not existing_user.get("officer_id"):
            existing_user["officer_id"] = f"OFFICER_GOOGLE_{len(users):03d}"
        save_users(users)
        db_user = existing_user
    else:
        num = 101 + len(users)
        db_user = {
            "username": email,
            "email": email,
            "google_sub": google_sub,
            "full_name": full_name,
            "role": user_role,
            "auth_provider": "google",
            "farmer_id": f"DEMO{num:03d}" if user_role == "farmer" else None,
            "officer_id": f"OFFICER_GOOGLE_{num:03d}" if user_role == "bank_officer" else None,
            "district": "Dharwad",
            "state": "Karnataka"
        }
        users.append(db_user)
        save_users(users)

    token_payload = {
        "sub": db_user["username"],
        "email": email,
        "role": user_role,
        "full_name": full_name,
        "farmer_id": db_user.get("farmer_id"),
        "officer_id": db_user.get("officer_id"),
        "auth_provider": "google"
    }

    access_token = create_access_token(token_payload)

    return {
        "status": "success",
        "message": f"Successfully authenticated via Google as {full_name} ({user_role.upper()}).",
        "access_token": access_token,
        "token_type": "bearer",
        "user": token_payload
    }

@router.get("/me")
def get_current_user_profile(current_user: Dict[str, Any] = Depends(get_current_user)):
    """Returns profile details for the current authenticated user."""
    return {
        "status": "success",
        "user": current_user
    }
