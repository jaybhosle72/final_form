"""
SHAP-style Feature Importance & Explainability Engine
Decomposes dynamic credit score changes into positive & negative point attributions.
"""

from typing import Dict, Any, List

class SHAPExplainabilityEngine:
    def explain_risk_drivers(self, risk_result: Dict[str, Any], app_data: Dict[str, Any]) -> Dict[str, Any]:
        cibil = int(app_data.get("cibilScore", 710))
        temp = float(app_data.get("temp", 28.0))
        rain_deficit = float(app_data.get("rainfallDeficitPct", 0.0))
        irrigation = str(app_data.get("irrigationType", "Rainfed"))
        fert = float(app_data.get("fertilizer", 75.0))
        dscr = float(risk_result.get("dscr", 1.2))

        shap_values: List[Dict[str, Any]] = []

        # 1. Financial History
        cibil_contrib = cibil - 700
        shap_values.append({
            "feature": "CIBIL / Credit History",
            "value": str(cibil),
            "impactPoints": cibil_contrib,
            "type": "positive" if cibil_contrib >= 0 else "negative",
            "description": "Solid historical financial track record." if cibil_contrib >= 0 else "Sub-optimal historical financial record."
        })

        # 2. Temperature Stress
        temp_impact = int(round(-(temp - 30.0) * 14.5)) if temp > 30.0 else int(round((30.0 - temp) * 3.5))
        shap_values.append({
            "feature": "Temperature / Heat Stress",
            "value": f"{temp}°C",
            "impactPoints": temp_impact,
            "type": "positive" if temp_impact >= 0 else "negative",
            "description": f"Elevated heat stress ({temp}°C) causes crop yield decay." if temp > 32.0 else "Optimal temperature for crop growth."
        })

        # 3. Rainfall Anomaly
        rain_impact = int(round(rain_deficit * 2.8)) if rain_deficit < 0 else int(round(min(40.0, rain_deficit * 1.5)))
        shap_values.append({
            "feature": "Monsoon Rainfall Anomaly",
            "value": f"{'+' if rain_deficit >= 0 else ''}{rain_deficit}%",
            "impactPoints": rain_impact,
            "type": "positive" if rain_impact >= 0 else "negative",
            "description": f"Severe rainfall deficit ({rain_deficit}%) increases drought risk." if rain_deficit < -15 else "Adequate monsoon rainfall coverage."
        })

        # 4. Irrigation Mitigation
        irr_impact = +65 if "Drip" in irrigation else (+45 if "Canal" in irrigation or "Tube-well" in irrigation else -35)
        shap_values.append({
            "feature": "Irrigation Infrastructure",
            "value": irrigation,
            "impactPoints": irr_impact,
            "type": "positive" if irr_impact >= 0 else "negative",
            "description": "Rainfed crop is vulnerable to drought." if "Rainfed" in irrigation else "Irrigation infrastructure buffers against heat & drought."
        })

        # 5. Debt Coverage Ratio
        dscr_impact = int(round((dscr - 1.2) * 40.0))
        shap_values.append({
            "feature": "Debt Service Coverage (DSCR)",
            "value": f"{dscr}x",
            "impactPoints": dscr_impact,
            "type": "positive" if dscr_impact >= 0 else "negative",
            "description": "Healthy cashflow margin to service loan EMI." if dscr >= 1.25 else "Tight farm revenue margin to cover debt."
        })

        # Officer Next Steps
        recommendations = risk_result.get("officer_next_steps", [])
        if not recommendations:
            if "Rainfed" in irrigation:
                recommendations.append("Grant 30% top-up micro-subsidy for installing Solar Drip Irrigation (+65 pts score boost).")
            if rain_deficit < -20 or temp > 33:
                recommendations.append("Mandatory enrollment in PM Fasal Bima Yojana Weather-Based Crop Insurance.")
            if fert < 65:
                recommendations.append("Recommend Soil Health Card test and balanced N-P-K fertilizer application.")
            if not recommendations:
                recommendations.append("Borrower exhibits low climate exposure. Approved for standard interest rate discount (-0.50%).")

        score = risk_result.get("climate_credit_score") or risk_result.get("climateCreditScore", 700)

        return {
            "shapValues": shap_values,
            "calculatedScore": score,
            "recommendations": recommendations
        }
