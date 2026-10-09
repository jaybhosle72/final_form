import os
import csv
import json
import re
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, Query, HTTPException, Depends, Request
from pydantic import BaseModel
from auth_service import get_optional_user, verify_farmer_ownership, get_current_user

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSV_PATH = os.path.join(BASE_DIR, "data", "synthetic_agricultural_loan_repayment_100_farmers.csv")
CATALOG_PATH = os.path.join(BASE_DIR, "data", "catalog.json")

router = APIRouter(prefix="/api/v2/farmers", tags=["Farmer Data Access Layer"])

def normalize_string(s: str) -> str:
    return re.sub(r'[^a-zA-Z0-9]', '', str(s)).upper()

def get_phone_number_for_farmer(farmer_id: str) -> str:
    """Generate deterministic sample registered phone number for testing."""
    num_str = re.sub(r'\D', '', farmer_id)
    num = int(num_str) if num_str else 1
    return f"+91 98765 {43200 + num:05d}"

def get_bank_details_for_farmer(farmer_id: str, income: float, loan: float) -> Dict[str, Any]:
    """Generate deterministic sample bank account & IFSC information for testing."""
    num_str = re.sub(r'\D', '', farmer_id)
    num = int(num_str) if num_str else 1
    
    bank_names = [
        "State Bank of India (NABARD Partner Branch)",
        "Bank of Baroda Agricultural Finance",
        "Punjab National Bank Rural Branch",
        "Canara Bank Farmer Credit Division",
        "Union Bank of India Agriculture Desk"
    ]
    ifsc_codes = ["SBIN0001540", "BARB0PUNEXX", "PUNB0123400", "CNRB0002410", "UBIN0532100"]
    
    bank_idx = (num - 1) % len(bank_names)
    acct_no = f"309874100{num:03d}"
    
    # Estimate balance based on annual farm income
    est_balance = round(max(5000.0, income * 0.15 + (num * 250)), 2)
    
    return {
        "bank_name": bank_names[bank_idx],
        "ifsc_code": ifsc_codes[bank_idx],
        "account_number_full": acct_no,
        "account_number_masked": f"XXXX-XXXX-{acct_no[-4:]}",
        "account_type": "Kisan Credit Card (KCC) Savings Account",
        "account_balance_inr": est_balance,
        "account_status": "Active / Verified"
    }

def calculate_derived_cibil_score(repayment_history: str, days_overdue: int, default_flag: int) -> int:
    """Derive numeric CIBIL credit score (300-900 scale) from repayment record."""
    if default_flag == 1 or days_overdue > 90:
        return max(300, 520 - (days_overdue * 2))
    elif "Repeated" in repayment_history or days_overdue > 30:
        return max(550, 620 - (days_overdue * 3))
    elif "Occasional" in repayment_history or days_overdue > 0:
        return 670 - min(40, days_overdue * 2)
    elif "Repaid" in repayment_history:
        return 760
    else:
        return 710

def load_all_farmers_data() -> List[Dict[str, Any]]:
    """Loads and maps the CSV dataset records to internal structured data models."""
    farmers = []
    if not os.path.exists(CSV_PATH):
        return farmers

    with open(CSV_PATH, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            fid = row.get("farmer_id", "").strip()
            income = float(row.get("estimated_annual_farm_income_inr", 0.0))
            loan_amt = float(row.get("loan_amount_inr", 0.0))
            dpd = int(row.get("days_past_due", 0))
            def_flag = int(row.get("default_flag", 0))
            rep_hist = row.get("previous_repayment_history", "No previous loan")

            phone = get_phone_number_for_farmer(fid)
            bank_info = get_bank_details_for_farmer(fid, income, loan_amt)
            cibil = calculate_derived_cibil_score(rep_hist, dpd, def_flag)

            mapped_record = {
                # Farmer Profile
                "farmer_id": fid,
                "loan_id": row.get("loan_id", "").strip(),
                "phone_number": phone,
                "phone_number_normalized": normalize_string(phone),
                "state": row.get("state", "").strip(),
                "district": row.get("district", "").strip(),
                "data_type": row.get("data_type", "SYNTHETIC_DEMO_NOT_REAL_FARMER_DATA"),
                
                # Bank & Financial Details (Sample data)
                "bank_details": bank_info,
                "financials": {
                    "estimated_annual_farm_income_inr": income,
                    "loan_amount_inr": loan_amt,
                    "loan_term_months": int(row.get("loan_term_months", 12)),
                    "annual_interest_rate_pct": float(row.get("annual_interest_rate_pct", 8.5)),
                    "loan_purpose": row.get("loan_purpose", "").strip()
                },

                # Credit History & Repayment Ledger
                "credit_history": {
                    "derived_cibil_score": cibil,
                    "previous_loan_count": int(row.get("previous_loan_count", 0)),
                    "previous_repayment_history": rep_hist,
                    "days_past_due": dpd,
                    "amount_overdue_inr": float(row.get("amount_overdue_inr", 0.0)),
                    "repayment_status": row.get("repayment_status", "").strip(),
                    "default_flag": def_flag
                },

                # Agricultural & Farm History
                "agricultural_history": {
                    "crop_type": row.get("crop_type", "").strip(),
                    "farm_area_acres": float(row.get("farm_area_acres", 0.0)),
                    "irrigation_type": row.get("irrigation_type", "").strip(),
                    "rainfall_deviation_pct": float(row.get("rainfall_deviation_pct", 0.0)),
                    "estimated_yield_change_pct": float(row.get("estimated_yield_change_pct", 0.0))
                }
            }
            farmers.append(mapped_record)

    return farmers

def filter_farmer_data_by_role(record: Dict[str, Any], role: str) -> Dict[str, Any]:
    """Applies role-based scoping to private financial information."""
    role_norm = role.lower().strip()
    
    # Scoped copy
    out = {
        "farmer_id": record["farmer_id"],
        "loan_id": record["loan_id"],
        "phone_number": record["phone_number"] if role_norm in ["bank_officer", "officer"] else "XXXXX-XXXXX",
        "state": record["state"],
        "district": record["district"],
        "data_type": record["data_type"],
        "agricultural_history": record["agricultural_history"],
        "financials": record["financials"]
    }

    if role_norm in ["bank_officer", "officer", "admin"]:
        # Unmasked full access for credit officers
        out["bank_details"] = record["bank_details"]
        out["credit_history"] = record["credit_history"]
    else:
        # Masked access for farmers / public
        b_masked = dict(record["bank_details"])
        b_masked["account_number_full"] = "RESTRICTED (Officer View Required)"
        b_masked["account_balance_inr"] = "RESTRICTED"
        out["bank_details"] = b_masked
        
        c_masked = dict(record["credit_history"])
        c_masked["derived_cibil_score"] = "RESTRICTED"
        c_masked["amount_overdue_inr"] = "RESTRICTED"
        out["credit_history"] = c_masked

    return out

@router.get("/search")
def search_farmers(
    request: Request,
    query: str = Query(..., description="Farmer ID (e.g. DEMO001), Loan ID (LOAN001), or Phone Number"),
    role: str = Query("farmer", description="Fallback role if token absent")
):
    """Searches for a farmer by Farmer ID, Loan ID, or Phone Number."""
    user = get_optional_user(request)
    effective_role = user.get("role") if user else role

    q_norm = normalize_string(query)
    if not q_norm:
        raise HTTPException(status_code=400, detail={"status": "error", "message": "Search query cannot be empty.", "code": "INVALID_QUERY"})

    farmers = load_all_farmers_data()
    matched = None
    
    for f in farmers:
        fid_norm = normalize_string(f["farmer_id"])
        lid_norm = normalize_string(f["loan_id"])
        ph_norm = f["phone_number_normalized"]
        
        if q_norm == fid_norm or q_norm == lid_norm or q_norm in ph_norm:
            matched = f
            break

    if not matched:
        raise HTTPException(status_code=404, detail={
            "status": "error",
            "message": f"No farmer record found matching identifier '{query}'.",
            "code": "FARMER_NOT_FOUND"
        })

    if user and user.get("role") == "farmer":
        verify_farmer_ownership(matched["farmer_id"], user)

    return {
        "status": "success",
        "matched_identifier": query,
        "role_applied": effective_role,
        "data": filter_farmer_data_by_role(matched, effective_role)
    }

@router.get("/{identifier}/profile")
def get_farmer_profile(
    identifier: str,
    request: Request,
    role: str = Query("farmer")
):
    """Retrieves farmer demographic and profile information."""
    user = get_optional_user(request)
    effective_role = user.get("role") if user else role

    farmers = load_all_farmers_data()
    id_norm = normalize_string(identifier)
    
    for f in farmers:
        if normalize_string(f["farmer_id"]) == id_norm or normalize_string(f["loan_id"]) == id_norm or id_norm in f["phone_number_normalized"]:
            if user and user.get("role") == "farmer":
                verify_farmer_ownership(f["farmer_id"], user)
            return {
                "status": "success",
                "farmer_id": f["farmer_id"],
                "loan_id": f["loan_id"],
                "phone_number": f["phone_number"] if effective_role.lower() == "bank_officer" else "XXXXX-XXXXX",
                "state": f["state"],
                "district": f["district"],
                "data_type": f["data_type"]
            }

    raise HTTPException(status_code=404, detail={
        "status": "error",
        "message": f"Farmer profile not found for '{identifier}'.",
        "code": "PROFILE_NOT_FOUND"
    })

@router.get("/{identifier}/financials")
def get_farmer_financials(
    identifier: str,
    request: Request,
    role: str = Query("farmer")
):
    """Retrieves linked sample bank account and financial information."""
    user = get_optional_user(request)
    effective_role = user.get("role") if user else role

    farmers = load_all_farmers_data()
    id_norm = normalize_string(identifier)
    
    for f in farmers:
        if normalize_string(f["farmer_id"]) == id_norm or normalize_string(f["loan_id"]) == id_norm or id_norm in f["phone_number_normalized"]:
            if user and user.get("role") == "farmer":
                verify_farmer_ownership(f["farmer_id"], user)
            scoped = filter_farmer_data_by_role(f, effective_role)
            return {
                "status": "success",
                "farmer_id": f["farmer_id"],
                "bank_details": scoped["bank_details"],
                "financials": scoped["financials"]
            }

    raise HTTPException(status_code=404, detail={
        "status": "error",
        "message": f"Financial details not found for '{identifier}'.",
        "code": "FINANCIALS_NOT_FOUND"
    })

@router.get("/{identifier}/credit-history")
def get_farmer_credit_history(
    identifier: str,
    request: Request,
    role: str = Query("bank_officer")
):
    """Retrieves credit scores, existing loans, and repayment history."""
    user = get_optional_user(request)
    effective_role = user.get("role") if user else role

    farmers = load_all_farmers_data()
    id_norm = normalize_string(identifier)
    
    for f in farmers:
        if normalize_string(f["farmer_id"]) == id_norm or normalize_string(f["loan_id"]) == id_norm or id_norm in f["phone_number_normalized"]:
            if user and user.get("role") == "farmer":
                verify_farmer_ownership(f["farmer_id"], user)
            scoped = filter_farmer_data_by_role(f, effective_role)
            return {
                "status": "success",
                "farmer_id": f["farmer_id"],
                "credit_history": scoped["credit_history"]
            }

    raise HTTPException(status_code=404, detail={
        "status": "error",
        "message": f"Credit history not found for '{identifier}'.",
        "code": "CREDIT_HISTORY_NOT_FOUND"
    })

@router.get("/{identifier}/agricultural-history")
def get_farmer_agricultural_history(
    identifier: str
):
    """Retrieves farm and agricultural history."""
    farmers = load_all_farmers_data()
    id_norm = normalize_string(identifier)
    
    for f in farmers:
        if normalize_string(f["farmer_id"]) == id_norm or normalize_string(f["loan_id"]) == id_norm or id_norm in f["phone_number_normalized"]:
            return {
                "status": "success",
                "farmer_id": f["farmer_id"],
                "crop_type": f["agricultural_history"]["crop_type"],
                "farm_area_acres": f["agricultural_history"]["farm_area_acres"],
                "irrigation_type": f["agricultural_history"]["irrigation_type"],
                "rainfall_deviation_pct": f["agricultural_history"]["rainfall_deviation_pct"],
                "estimated_yield_change_pct": f["agricultural_history"]["estimated_yield_change_pct"]
            }

    raise HTTPException(status_code=404, detail={
        "status": "error",
        "message": f"Agricultural history not found for '{identifier}'.",
        "code": "AGRI_HISTORY_NOT_FOUND"
    })

@router.get("/{identifier}/full")
def get_full_farmer_record(
    identifier: str,
    request: Request,
    role: str = Query("farmer")
):
    """Retrieves full matching farmer record scoped by user role."""
    user = get_optional_user(request)
    effective_role = user.get("role") if user else role

    farmers = load_all_farmers_data()
    id_norm = normalize_string(identifier)
    
    for f in farmers:
        if normalize_string(f["farmer_id"]) == id_norm or normalize_string(f["loan_id"]) == id_norm or id_norm in f["phone_number_normalized"]:
            if user and user.get("role") == "farmer":
                verify_farmer_ownership(f["farmer_id"], user)
            return {
                "status": "success",
                "role_applied": effective_role,
                "data": filter_farmer_data_by_role(f, effective_role)
            }

    raise HTTPException(status_code=404, detail={
        "status": "error",
        "message": f"Farmer record not found for '{identifier}'.",
        "code": "FARMER_NOT_FOUND"
    })

@router.get("/me/dashboard")
def get_logged_in_farmer_dashboard(
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Retrieves full personalized dashboard data for the authenticated farmer."""
    farmer_id = current_user.get("farmer_id") or "DEMO001"
    farmers = load_all_farmers_data()
    matched_records = [f for f in farmers if normalize_string(f["farmer_id"]) == normalize_string(farmer_id)]
    
    if not matched_records:
        matched = farmers[0] if farmers else {}
        matched_records = [matched]
    else:
        matched = matched_records[0]

    user_role = current_user.get("role", "farmer")
    scoped_data = filter_farmer_data_by_role(matched, user_role)

    decisions_path = os.path.join(BASE_DIR, "data", "lending_decisions.json")
    decisions = []
    if os.path.exists(decisions_path):
        try:
            with open(decisions_path, "r", encoding="utf-8") as df:
                decisions = json.load(df)
        except Exception:
            pass

    dec_map = {}
    for d in decisions:
        if d.get("application_id"):
            dec_map[d.get("application_id")] = d
        if d.get("farmer_id"):
            dec_map[d.get("farmer_id")] = d

    application_history = []
    for idx, rec in enumerate(matched_records):
        lid = rec.get("loan_id", "")
        if lid.startswith("APP-2026-"):
            app_id_code = lid
        else:
            num_part = re.sub(r'\D', '', lid) or str(idx + 1)
            app_id_code = f"APP-2026-{(8000 + int(num_part)):04d}"

        my_decision = dec_map.get(app_id_code) or dec_map.get(lid) or dec_map.get(matched["farmer_id"])

        rec_status = "Submitted"
        if my_decision:
            d_val = str(my_decision.get("decision", "")).upper()
            if d_val in ["APPROVED", "APPROVE"]:
                rec_status = "Approved"
            elif d_val in ["REJECTED", "REJECT"]:
                rec_status = "Rejected"
            elif "CONDITIONAL" in d_val or "INFO" in d_val:
                rec_status = "Additional Information Required"
            elif "REVIEW" in d_val:
                rec_status = "Under Review"

        application_history.append({
            "application_id": app_id_code,
            "loan_id": rec["loan_id"],
            "requested_amount_inr": rec["financials"]["loan_amount_inr"],
            "loan_purpose": rec["financials"]["loan_purpose"],
            "crop_type": rec["agricultural_history"]["crop_type"],
            "farm_area_acres": rec["agricultural_history"]["farm_area_acres"],
            "status": rec_status,
            "submission_date": "2026-10-09",
            "officer_notes": my_decision.get("officer_notes") if my_decision else "Application placed in Bank Officer review queue."
        })

    primary_app_status = application_history[0]["status"] if application_history else "Submitted"

    return {
        "status": "success",
        "authenticated_user": {
            "username": current_user.get("sub"),
            "full_name": current_user.get("full_name", matched.get("farmer_id")),
            "role": user_role,
            "farmer_id": matched["farmer_id"],
            "identity_verification_status": "KCC Account Verified & Aadhaar Linked"
        },
        "profile": {
            "farmer_id": matched["farmer_id"],
            "state": matched["state"],
            "district": matched["district"],
            "phone_number": matched["phone_number"]
        },
        "bank_summary": scoped_data["bank_details"],
        "credit_summary": scoped_data["credit_history"],
        "agricultural_summary": matched["agricultural_history"],
        "application_status": primary_app_status,
        "applications": application_history
    }

@router.get("/me/application-prefill")
def get_farmer_application_prefill(
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Retrieves verified dataset fields to prefill the Loan Application Form."""
    farmer_id = current_user.get("farmer_id") or "DEMO001"
    farmers = load_all_farmers_data()
    matched = None
    for f in farmers:
        if normalize_string(f["farmer_id"]) == normalize_string(farmer_id):
            matched = f
            break
            
    if not matched and farmers:
        matched = farmers[0]

    return {
        "status": "success",
        "prefilled": {
            "applicant_name": current_user.get("full_name") or f"Farmer ({matched['farmer_id']})",
            "phone_number": matched["phone_number"],
            "identity_verification_status": "KCC Verified & Aadhaar Linked",
            "district": matched["district"],
            "state": matched["state"],
            "village_taluka": f"{matched['district']} Rural Sector 4",
            "crop_type": matched["agricultural_history"]["crop_type"],
            "farm_area_acres": matched["agricultural_history"]["farm_area_acres"],
            "irrigation_type": matched["agricultural_history"]["irrigation_type"],
            "water_source": "Borewell / District Canal Grid",
            "soil_type": "Loamy Topsoil (pH 6.8)",
            "previous_crop_yield_tons_ha": 4.5,
            "estimated_annual_income_inr": matched["financials"]["estimated_annual_farm_income_inr"],
            "existing_loan_amount_inr": matched["financials"]["loan_amount_inr"],
            "existing_loan_purpose": matched["financials"]["loan_purpose"],
            "existing_obligations_inr": matched["credit_history"]["amount_overdue_inr"],
            "land_document_status": "7/12 Pahani Record Verified in State Land Registry"
        },
        "retrieved_fields": [
            "applicant_name", "phone_number", "district", "state",
            "crop_type", "farm_area_acres", "irrigation_type",
            "estimated_annual_income_inr", "land_document_status"
        ]
    }
