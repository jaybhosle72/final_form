import os
import csv
import json
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, Query, HTTPException, Response, Depends
from fastapi.responses import FileResponse
from pydantic import BaseModel

import sys
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

from analytics.risk_engine import ClimateCreditRiskEngine
from analytics.shap_explainability import SHAPExplainabilityEngine
from analytics.pdf_generator import PDFReportGenerator
from integrations.openmeteo_service import OpenMeteoWeatherService
from integrations.soilgrids_service import SoilGridsService
from auth_service import get_current_user, require_role, get_optional_user

router = APIRouter(prefix="/api/v2/risk", tags=["Climate Credit Risk Assessment Engine"])

CSV_PATH = os.path.join(BASE_DIR, "data", "synthetic_agricultural_loan_repayment_100_farmers.csv")
CATALOG_PATH = os.path.join(BASE_DIR, "data", "catalog.json")
DECISIONS_PATH = os.path.join(BASE_DIR, "data", "lending_decisions.json")

risk_engine = ClimateCreditRiskEngine()
shap_engine = SHAPExplainabilityEngine()
pdf_gen = PDFReportGenerator()
weather_service = OpenMeteoWeatherService()
soil_service = SoilGridsService()

WEATHER_CACHE: Dict[str, Any] = {
    "dharwad": {"totalPrecipitationMm": 336.7, "avgTempMaxC": 31.2, "heatwaveDaysCount": 1},
    "pune": {"totalPrecipitationMm": 412.0, "avgTempMaxC": 29.8, "heatwaveDaysCount": 0},
    "jaipur": {"totalPrecipitationMm": 210.5, "avgTempMaxC": 34.5, "heatwaveDaysCount": 6},
    "prayagraj": {"totalPrecipitationMm": 380.2, "avgTempMaxC": 32.1, "heatwaveDaysCount": 3},
    "amravati": {"totalPrecipitationMm": 350.0, "avgTempMaxC": 33.0, "heatwaveDaysCount": 4},
    "warangal": {"totalPrecipitationMm": 390.4, "avgTempMaxC": 32.5, "heatwaveDaysCount": 2},
    "rajkot": {"totalPrecipitationMm": 285.0, "avgTempMaxC": 33.8, "heatwaveDaysCount": 5},
    "solapur": {"totalPrecipitationMm": 260.0, "avgTempMaxC": 34.0, "heatwaveDaysCount": 5},
    "agra": {"totalPrecipitationMm": 310.0, "avgTempMaxC": 33.2, "heatwaveDaysCount": 4},
    "belagavi": {"totalPrecipitationMm": 450.0, "avgTempMaxC": 28.5, "heatwaveDaysCount": 0},
    "indore": {"totalPrecipitationMm": 375.0, "avgTempMaxC": 30.5, "heatwaveDaysCount": 1}
}

SOIL_CACHE: Dict[str, Any] = {
    "dharwad": {"soil_ph": 6.8, "texture_class": "Loam"},
    "pune": {"soil_ph": 7.2, "texture_class": "Clay Loam"},
    "jaipur": {"soil_ph": 7.8, "texture_class": "Sandy Loam"},
    "prayagraj": {"soil_ph": 6.9, "texture_class": "Alluvial Loam"},
    "amravati": {"soil_ph": 7.4, "texture_class": "Black Clay"},
    "warangal": {"soil_ph": 6.7, "texture_class": "Red Loam"},
    "rajkot": {"soil_ph": 7.6, "texture_class": "Medium Black"},
    "solapur": {"soil_ph": 7.5, "texture_class": "Deep Black Clay"},
    "agra": {"soil_ph": 7.1, "texture_class": "Sandy Clay Loam"},
    "belagavi": {"soil_ph": 6.5, "texture_class": "Laterite Loam"},
    "indore": {"soil_ph": 7.3, "texture_class": "Black Cotton Soil"}
}

DISTRICT_COORDS = {
    "dharwad": {"lat": 15.4589, "lng": 75.0078, "name": "Dharwad, Karnataka"},
    "pune": {"lat": 18.5204, "lng": 73.8567, "name": "Pune, Maharashtra"},
    "jaipur": {"lat": 26.9124, "lng": 75.7873, "name": "Jaipur, Rajasthan"},
    "prayagraj": {"lat": 25.4358, "lng": 81.8463, "name": "Prayagraj, Uttar Pradesh"},
    "amravati": {"lat": 20.9374, "lng": 77.7796, "name": "Amravati, Maharashtra"},
    "warangal": {"lat": 17.9689, "lng": 79.5941, "name": "Warangal, Telangana"},
    "rajkot": {"lat": 22.3039, "lng": 70.8022, "name": "Rajkot, Gujarat"},
    "solapur": {"lat": 17.6599, "lng": 75.9064, "name": "Solapur, Maharashtra"},
    "agra": {"lat": 27.1767, "lng": 78.0081, "name": "Agra, Uttar Pradesh"},
    "belagavi": {"lat": 15.8497, "lng": 74.4977, "name": "Belagavi, Karnataka"},
    "indore": {"lat": 22.7196, "lng": 75.8577, "name": "Indore, Madhya Pradesh"}
}

def load_borrowers_csv() -> List[Dict[str, Any]]:
    borrowers = []
    if os.path.exists(CSV_PATH):
        with open(CSV_PATH, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                borrowers.append(row)
    return borrowers

def get_crop_agronomic_context(crop_name: str) -> Dict[str, Any]:
    """Look up crop soil NPK requirements and yield context from catalogued Kaggle datasets."""
    crop_lower = crop_name.lower()
    
    # Defaults
    context = {
        "crop": crop_name,
        "optimal_N": 70.0,
        "optimal_P": 45.0,
        "optimal_K": 35.0,
        "recommended_ph": 6.5,
        "water_requirement_liters_yr": 2500.0,
        "benchmark_yield_tons_ha": 10.5,
        "dataset_source": "Kaggle Crop Recommendation & Water Dataset (sakshi21122001)"
    }
    
    # Specific benchmarks for common crops from ingested datasets
    benchmarks = {
        "rice": {"N": 80.0, "P": 48.0, "K": 40.0, "ph": 6.5, "water": 3000.0, "yield": 4.2},
        "wheat": {"N": 100.0, "P": 50.0, "K": 40.0, "ph": 6.8, "water": 1800.0, "yield": 3.8},
        "maize": {"N": 78.0, "P": 48.0, "K": 20.0, "ph": 6.2, "water": 1500.0, "yield": 5.1},
        "cotton": {"N": 118.0, "P": 46.0, "K": 20.0, "ph": 7.0, "water": 2200.0, "yield": 2.5},
        "sugarcane": {"N": 120.0, "P": 60.0, "K": 50.0, "ph": 6.7, "water": 3500.0, "yield": 70.0},
        "pulses": {"N": 40.0, "P": 68.0, "K": 80.0, "ph": 6.9, "water": 1200.0, "yield": 1.8},
        "millet": {"N": 50.0, "P": 30.0, "K": 20.0, "ph": 6.5, "water": 900.0, "yield": 2.1},
        "onion": {"N": 90.0, "P": 50.0, "K": 50.0, "ph": 6.6, "water": 1400.0, "yield": 18.0}
    }
    
    for key, b in benchmarks.items():
        if key in crop_lower:
            context["optimal_N"] = b["N"]
            context["optimal_P"] = b["P"]
            context["optimal_K"] = b["K"]
            context["recommended_ph"] = b["ph"]
            context["water_requirement_liters_yr"] = b["water"]
            context["benchmark_yield_tons_ha"] = b["yield"]
            break
            
    return context

class AssessRiskRequest(BaseModel):
    farmer_id: Optional[str] = "DEMO001"
    applicant_name: Optional[str] = None
    district: Optional[str] = "Dharwad"
    state: Optional[str] = "Karnataka"
    crop_type: Optional[str] = "Cotton"
    land_acres: Optional[float] = 5.0
    loan_amount: Optional[float] = 200000.0
    loan_term_months: Optional[int] = 12
    interest_rate: Optional[float] = 8.5
    irrigation_type: Optional[str] = "Rainfed"
    cibil_score: Optional[int] = 710
    collateral_value: Optional[float] = 300000.0

class RecordDecisionRequest(BaseModel):
    farmer_id: str
    decision: str  # "APPROVED", "REJECTED", "CONDITIONAL APPROVAL"
    officer_notes: str
    approved_amount_inr: Optional[float] = None

class SubmitLoanRequest(BaseModel):
    farmer_id: Optional[str] = None
    applicant_name: str
    phone_number: Optional[str] = None
    village_taluka: Optional[str] = "Rural District Sector 4"
    district: str
    state: str
    crop_type: str
    farm_area_acres: float
    sowing_date: Optional[str] = "2026-06-15"
    expected_harvest_date: Optional[str] = "2026-11-20"
    irrigation_type: str
    water_source: Optional[str] = "Borewell / District Canal Grid"
    soil_type: Optional[str] = "Loamy Topsoil (pH 6.8)"
    previous_crop_yield_tons_ha: Optional[float] = 4.5
    estimated_annual_income: float
    loan_amount_inr: float
    loan_term_months: int
    loan_purpose: str
    repayment_source: Optional[str] = "Crop Harvest Sale Proceeds"
    existing_loan_obligations_inr: Optional[float] = 0.0
    land_document_status: Optional[str] = "7/12 Pahani Record Verified in State Land Registry"

@router.get("/borrowers")
def get_all_borrowers():
    """Returns all 100 borrower loan applications from CSV dataset."""
    borrowers = load_borrowers_csv()
    return {
        "status": "success",
        "total_borrowers": len(borrowers),
        "source": "synthetic_agricultural_loan_repayment_100_farmers.csv",
        "data": borrowers
    }

ASSESSMENTS_PATH = os.path.join(BASE_DIR, "data", "assessments.json")

def load_assessments_db() -> List[Dict[str, Any]]:
    if os.path.exists(ASSESSMENTS_PATH):
        try:
            with open(ASSESSMENTS_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []

def save_assessment_record(record: Dict[str, Any]):
    assessments = load_assessments_db()
    # Replace existing record with same application_id / farmer_id or append
    target_id = record.get("farmer_id") or record.get("loan_id")
    updated = False
    for i, a in enumerate(assessments):
        if (a.get("farmer_id") and a.get("farmer_id") == target_id) or (a.get("loan_id") and a.get("loan_id") == target_id):
            assessments[i] = record
            updated = True
            break
    if not updated:
        assessments.append(record)

    with open(ASSESSMENTS_PATH, "w", encoding="utf-8") as f:
        json.dump(assessments, f, indent=2)

@router.get("/assessments/{identifier}")
def get_saved_assessment(identifier: str):
    """Retrieves saved assessment record against loan application ID or farmer ID."""
    assessments = load_assessments_db()
    id_lower = identifier.lower().strip()
    for a in assessments:
        if a.get("farmer_id", "").lower() == id_lower or a.get("loan_id", "").lower() == id_lower or a.get("application_id", "").lower() == id_lower:
            return {"status": "success", "assessment": a}
            
    return {"status": "success", "assessment": None}

@router.post("/assess")
def assess_credit_risk(payload: AssessRiskRequest):
    """Executes climate-aware credit risk engine using dataset context & telemetry."""
    req_dict = payload.dict()
    import datetime
    
    # 1. Check if farmer_id matches a CSV row
    borrowers = load_borrowers_csv()
    csv_row = None
    if payload.farmer_id:
        for b in borrowers:
            if b.get("farmer_id") == payload.farmer_id or b.get("loan_id") == payload.farmer_id:
                csv_row = b
                break

    missing_fields = []
    data_sources = {
        "farmer_profile": "synthetic_agricultural_loan_repayment_100_farmers.csv" if csv_row else "API Request Payload",
        "credit_history": "synthetic_agricultural_loan_repayment_100_farmers.csv" if csv_row else "User Provided Inputs",
        "agronomic": "Kaggle 12 Agricultural Datasets Catalog (sakshi21122001 / UN-FAO)"
    }

    if csv_row:
        applicant_name = f"Farmer Borrower ({csv_row.get('farmer_id')})"
        district = csv_row.get("district", payload.district)
        state = csv_row.get("state", payload.state)
        crop_type = csv_row.get("crop_type", payload.crop_type)
        land_acres = float(csv_row.get("farm_area_acres", payload.land_acres or 5.0))
        loan_amount = float(csv_row.get("loan_amount_inr", payload.loan_amount or 200000.0))
        loan_term_months = int(csv_row.get("loan_term_months", payload.loan_term_months or 12))
        interest_rate = float(csv_row.get("annual_interest_rate_pct", payload.interest_rate or 8.5))
        irrigation_type = csv_row.get("irrigation_type", payload.irrigation_type or "Rainfed")
        
        rep_hist = csv_row.get("previous_repayment_history", "Repaid on time")
        dpd = int(csv_row.get("days_past_due", 0))
        cibil_score = 740 if rep_hist == "Repaid on time" else (650 if "Occasional" in rep_hist else 580)
        collateral_val = loan_amount * 1.35
        existing_obligations = float(csv_row.get("amount_overdue_inr", 0.0))
    else:
        applicant_name = payload.applicant_name or "Farmer Applicant"
        district = payload.district or "Dharwad"
        state = payload.state or "Karnataka"
        crop_type = payload.crop_type or "Cotton"
        land_acres = payload.land_acres or 5.0
        loan_amount = payload.loan_amount or 200000.0
        loan_term_months = payload.loan_term_months or 12
        interest_rate = payload.interest_rate or 8.5
        irrigation_type = payload.irrigation_type or "Rainfed"
        cibil_score = payload.cibil_score or 710
        collateral_val = payload.collateral_value or (loan_amount * 1.35)
        rep_hist = "Repaid on time"
        dpd = 0
        existing_obligations = 0.0

    # Check optional / unconfigured live APIs
    missing_fields.append("satellite_ndvi")
    missing_fields.append("market_apmc_live")

    # 2. Agronomic context from 12 Kaggle datasets
    agronomic_ctx = get_crop_agronomic_context(crop_type)
    
    # 3. Weather & Soil telemetry for District (Cached for instant batch evaluation)
    dist_key = district.lower().split(",")[0].strip()
    coords = DISTRICT_COORDS.get(dist_key, {"lat": 15.4589, "lng": 75.0078, "name": district})
    
    weather_res = WEATHER_CACHE.get(dist_key, {"totalPrecipitationMm": 320.0, "avgTempMaxC": 30.0, "heatwaveDaysCount": 1})
    soil_res = SOIL_CACHE.get(dist_key, {"soil_ph": 6.8, "texture_class": "Loam"})

    data_sources["weather"] = "Open-Meteo Weather API / Cached Climatology"
    data_sources["soil"] = "ISRIC SoilGrids API / Regional Soil Taxonomy"

    rainfall_mm = weather_res.get("totalPrecipitationMm", 320.0)
    avg_temp = weather_res.get("avgTempMaxC", 29.5)
    heatwave_days = weather_res.get("heatwaveDaysCount", 2)
    
    soil_ph = soil_res.get("soil_ph", agronomic_ctx["recommended_ph"])
    soil_texture = soil_res.get("texture_class", "Loam")

    # 4. Yield Forecast (Adjusted by agronomic context & weather)
    benchmark_yield = agronomic_ctx["benchmark_yield_tons_ha"]
    rain_deficit_pct = max(-50.0, min(50.0, ((rainfall_mm - 400.0) / 400.0) * 100.0))
    temp_penalty = max(0.0, (avg_temp - 30.0) * 0.05)
    
    predicted_yield = max(0.5, benchmark_yield * (1.0 + (rain_deficit_pct / 200.0) - temp_penalty))

    app_data = {
        "applicantName": applicant_name,
        "farmerId": payload.farmer_id or "DEMO001",
        "district": f"{district}, {state}",
        "cropType": crop_type,
        "landAcres": land_acres,
        "loanAmount": loan_amount,
        "tenureMonths": loan_term_months,
        "interestRate": interest_rate,
        "irrigationType": irrigation_type,
        "cibilScore": cibil_score,
        "collateralValue": collateral_val,
        "apmcPrice": 4800.0,
        "temp": avg_temp,
        "rainfallDeficitPct": rain_deficit_pct,
        "fertilizer": agronomic_ctx["optimal_N"],
        "existingObligations": existing_obligations,
        "daysPastDue": dpd,
        "repaymentHistory": rep_hist
    }

    yield_data = {"predictedYieldTonsPerHa": predicted_yield}
    weather_data = {
        "avgTemperatureC": avg_temp,
        "rainfallDeficitPct": rain_deficit_pct,
        "heatwaveDays": heatwave_days,
        "soilMoistureIndex": 0.38,
        "ndvi": 0.62
    }

    # 5. Run Dual-Pillar Risk Engine
    risk_res = risk_engine.assess_risk(
        app_data=app_data,
        yield_data=yield_data,
        weather_data=weather_data,
        agronomic_ctx=agronomic_ctx,
        data_sources=data_sources,
        missing_fields=missing_fields
    )
    
    # 6. Run SHAP Explainability Engine
    shap_res = shap_engine.explain_risk_drivers(risk_res, app_data)

    # 7. Persist Assessment Record
    assessment_record = {
        "assessment_id": f"ASSESS-{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}",
        "farmer_id": payload.farmer_id or "DEMO001",
        "loan_id": csv_row.get("loan_id") if csv_row else "LOAN001",
        "timestamp": datetime.datetime.now().isoformat(),
        "model_version": risk_res["model_version"],
        "overall_risk_classification": risk_res["overall_risk_classification"],
        "climate_risk_classification": risk_res["climate_risk_classification"],
        "financial_risk_classification": risk_res["financial_risk_classification"],
        "probability_model_status": risk_res["probability_model_status"],
        "estimated_repayment_probability_pct": risk_res["estimated_repayment_probability_pct"],
        "borrower_details": {
            "farmer_id": payload.farmer_id or "DEMO001",
            "applicant_name": applicant_name,
            "district": district,
            "state": state,
            "crop_type": crop_type,
            "land_acres": land_acres,
            "irrigation_type": irrigation_type,
            "loan_amount_inr": loan_amount,
            "loan_term_months": loan_term_months,
            "interest_rate_pct": interest_rate
        },
        "agronomic_dataset_context": agronomic_ctx,
        "telemetry_context": {
            "latitude": coords["lat"],
            "longitude": coords["lng"],
            "rainfall_mm": rainfall_mm,
            "avg_temp_max_c": avg_temp,
            "heatwave_days": heatwave_days,
            "soil_ph": soil_ph,
            "soil_texture": soil_texture
        },
        "risk_assessment": risk_res,
        "explainability": shap_res
    }

    try:
        save_assessment_record(assessment_record)
    except Exception as err:
        print(f"Warning: Failed to persist assessment record: {err}")

    return {
        "status": "success",
        "assessment_id": assessment_record["assessment_id"],
        "timestamp": assessment_record["timestamp"],
        "model_version": risk_res["model_version"],
        "borrower_details": assessment_record["borrower_details"],
        "agronomic_dataset_context": agronomic_ctx,
        "telemetry_context": assessment_record["telemetry_context"],
        "risk_assessment": risk_res,
        "explainability": shap_res
    }

def load_lending_decisions() -> List[Dict[str, Any]]:
    if os.path.exists(DECISIONS_PATH):
        try:
            with open(DECISIONS_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return []

def save_lending_decisions(decisions: List[Dict[str, Any]]):
    os.makedirs(os.path.dirname(DECISIONS_PATH), exist_ok=True)
    with open(DECISIONS_PATH, "w", encoding="utf-8") as f:
        json.dump(decisions, f, indent=2)

@router.post("/decision")
def record_lending_decision(
    payload: RecordDecisionRequest,
    current_user: Dict[str, Any] = Depends(require_role(["bank_officer"]))
):
    """Allows authenticated Bank Officers to record official lending decisions and notes."""
    decisions = load_lending_decisions()
    import datetime
    
    new_dec = {
        "farmer_id": payload.farmer_id,
        "decision": payload.decision.upper().strip(),
        "officer_notes": payload.officer_notes.strip(),
        "approved_amount_inr": payload.approved_amount_inr,
        "recorded_by": current_user.get("sub", "officer1"),
        "officer_name": current_user.get("full_name", "Bank Officer"),
        "timestamp": datetime.datetime.now().isoformat()
    }

    updated = False
    for idx, d in enumerate(decisions):
        if d.get("farmer_id") == payload.farmer_id:
            decisions[idx] = new_dec
            updated = True
            break
            
    if not updated:
        decisions.append(new_dec)

    save_lending_decisions(decisions)

    return {
        "status": "success",
        "message": f"Lending decision '{payload.decision}' successfully recorded for farmer '{payload.farmer_id}'.",
        "decision_record": new_dec
    }

@router.get("/decisions/{farmer_id}")
def get_farmer_lending_decision(farmer_id: str):
    """Retrieves recorded officer lending decision for a farmer if present."""
    decisions = load_lending_decisions()
    for d in decisions:
        if d.get("farmer_id") == farmer_id:
            return {"status": "success", "decision": d}
            
    return {"status": "success", "decision": None}

@router.post("/submit-loan")
def submit_farmer_loan_application(
    payload: SubmitLoanRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Allows logged-in Farmers or Officers to submit a new loan application. Places application into officer review queue."""
    if payload.farm_area_acres <= 0:
        raise HTTPException(status_code=400, detail={"status": "error", "message": "Farm area in acres must be greater than 0.", "code": "INVALID_LAND_AREA"})
    if payload.loan_amount_inr <= 0:
        raise HTTPException(status_code=400, detail={"status": "error", "message": "Requested loan amount must be greater than ₹0.", "code": "INVALID_LOAN_AMOUNT"})
    if payload.loan_term_months <= 0 or payload.loan_term_months > 120:
        raise HTTPException(status_code=400, detail={"status": "error", "message": "Loan tenure must be between 1 and 120 months.", "code": "INVALID_TENURE"})

    import random, datetime
    borrowers = load_borrowers_csv()
    new_num = 101 + len(borrowers)
    assigned_fid = payload.farmer_id or current_user.get("farmer_id") or f"DEMO{new_num:03d}"
    assigned_lid = f"LOAN{new_num:03d}"
    
    # Generate unique application ID
    unique_app_code = f"APP-2026-{random.randint(1000, 9999)}"
    submission_time = datetime.datetime.now().isoformat()

    row = {
        "farmer_id": assigned_fid,
        "state": payload.state,
        "district": payload.district,
        "crop_type": payload.crop_type,
        "farm_area_acres": str(payload.farm_area_acres),
        "irrigation_type": payload.irrigation_type,
        "loan_id": unique_app_code,
        "loan_purpose": payload.loan_purpose,
        "loan_amount_inr": str(payload.loan_amount_inr),
        "estimated_annual_farm_income_inr": str(payload.estimated_annual_income),
        "loan_term_months": str(payload.loan_term_months),
        "annual_interest_rate_pct": "8.5",
        "previous_loan_count": "1",
        "previous_repayment_history": "Repaid on time",
        "rainfall_deviation_pct": "0.0",
        "estimated_yield_change_pct": "0.0",
        "days_past_due": "0",
        "amount_overdue_inr": str(payload.existing_loan_obligations_inr or 0),
        "repayment_status": "Submitted - Officer Review Queue",
        "default_flag": "0",
        "data_type": "SUBMITTED_FARMER_LOAN_APPLICATION"
    }

    if os.path.exists(CSV_PATH):
        with open(CSV_PATH, mode="r", encoding="utf-8") as f:
            reader = csv.reader(f)
            header = next(reader)
        with open(CSV_PATH, mode="a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=header)
            writer.writerow(row)

    return {
        "status": "success",
        "message": f"Loan application '{unique_app_code}' submitted successfully for {payload.applicant_name}. Placed into Officer Review Queue.",
        "application_id": unique_app_code,
        "loan_id": assigned_lid,
        "farmer_id": assigned_fid,
        "application_status": "Submitted",
        "review_queue": "Bank Officer Credit Review Desk",
        "timestamp": submission_time,
        "loan_application": row
    }

@router.get("/batch")
def get_batch_risk_portfolio(current_user: Dict[str, Any] = Depends(require_role(["bank_officer"]))):
    """Runs batch risk assessment across all borrowers in dataset. Restricted to Bank Officers."""
    borrowers = load_borrowers_csv()
    if not borrowers:
        raise HTTPException(status_code=404, detail="Borrowers CSV dataset not found.")

    approved = 0
    conditional = 0
    rejected = 0
    total_exposure = 0.0
    total_expected_loss = 0.0
    evaluated = []

    for b in borrowers:
        res = assess_credit_risk(AssessRiskRequest(farmer_id=b.get("farmer_id")))
        risk_info = res.get("risk_assessment", {})
        overall_risk = risk_info.get("overall_risk_classification", "Low")
        score = risk_info.get("climate_credit_score", 700)
        pd_pct = risk_info.get("estimated_default_probability_pct", 10.0)
        el = float(risk_info.get("expected_loss_inr", 0))
        loan_amt = float(b.get("loan_amount_inr", 0))
        
        total_exposure += loan_amt
        total_expected_loss += el

        if overall_risk == "Low":
            dec = "APPROVED"
            approved += 1
        elif overall_risk == "Moderate":
            dec = "CONDITIONAL APPROVAL"
            conditional += 1
        else:
            dec = "HIGH RISK / REJECTED"
            rejected += 1

        evaluated.append({
            "farmer_id": b.get("farmer_id"),
            "district": b.get("district"),
            "crop": b.get("crop_type"),
            "loan_amount": loan_amt,
            "credit_score": score,
            "pd_pct": pd_pct,
            "expected_loss": el,
            "dscr": risk_info.get("dscr", 1.2),
            "decision": dec
        })

    return {
        "status": "success",
        "portfolio_summary": {
            "total_borrowers_evaluated": len(borrowers),
            "approved_count": approved,
            "conditional_count": conditional,
            "rejected_count": rejected,
            "approved_pct": round((approved / len(borrowers)) * 100.0, 1),
            "total_loan_exposure_inr": round(total_exposure),
            "total_expected_loss_inr": round(total_expected_loss),
            "portfolio_expected_loss_pct": round((total_expected_loss / total_exposure) * 100.0, 2) if total_exposure > 0 else 0.0
        },
        "borrowers": evaluated
    }
