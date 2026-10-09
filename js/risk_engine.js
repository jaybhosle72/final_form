// NABARD FIN-03 Dynamic Climate-Aware Credit Risk Assessment Engine

class ClimateCreditRiskEngine {
  constructor() {
    this.yieldPredictor = yieldPredictor || new MLYieldPredictor();
  }

  /**
   * Assesses loan applicant credit risk integrating soil, weather, yield, market prices, & financial records.
   * @param {Object} appData 
   * @returns {Object} Full Risk Assessment Result
   */
  assessCreditRisk(appData) {
    // 1. Extract & Sanitize Inputs (Preventing overflow / unrealistic bounds)
    const loanAmount = Math.max(10000, Math.min(5000000, parseFloat(appData.loanAmount || 250000))); // ₹ 10k to 50L
    const tenureMonths = Math.max(3, Math.min(60, parseInt(appData.tenureMonths || 12)));
    // Clamp land acres between 0.1 and 100 acres max
    const landAcres = Math.max(0.1, Math.min(100, parseFloat(appData.landAcres || 5)));
    const cibilScore = Math.max(300, Math.min(850, parseInt(appData.cibilScore || 710)));
    const collateralValue = Math.max(0, parseFloat(appData.collateralValue || 350000));
    const apmcPrice = Math.max(1000, Math.min(25000, parseFloat(appData.apmcPrice || 4800))); // ₹ / quintal
    const interestRate = parseFloat(appData.interestRate || 8.5); // % per annum

    // Agronomic / Weather inputs
    const fert = Math.max(10, Math.min(200, parseFloat(appData.fertilizer || 75)));
    const temp = Math.max(10, Math.min(50, parseFloat(appData.temp || 28)));
    const N = Math.max(10, Math.min(200, parseFloat(appData.N || 75)));
    const P = Math.max(5, Math.min(100, parseFloat(appData.P || 22)));
    const K = Math.max(5, Math.min(100, parseFloat(appData.K || 19)));
    const irrigationType = appData.irrigationType || 'Rainfed';
    
    // Climate & Satellite Anomaly Overrides
    const rainDeficit = Math.max(-80, Math.min(100, parseFloat(appData.rainfallDeficitPct || 0))); // e.g. -25%
    const soilMoisture = Math.max(0.05, Math.min(1.0, parseFloat(appData.soilMoisture || 0.45))); // 0.0 to 1.0
    const ndvi = Math.max(0.05, Math.min(1.0, parseFloat(appData.ndvi || 0.65))); // 0.1 to 0.9

    // 2. ML Crop Yield & Revenue Forecasting
    const yieldResult = this.yieldPredictor.predictYield({
      fertilizer: fert,
      temp: temp,
      N: N,
      P: P,
      K: K,
      irrigationType: irrigationType
    });

    // Climate-driven additional yield reduction from severe rainfall deficit & soil moisture drop
    let climateYieldFactor = 1.0;
    if (rainDeficit < 0) {
      let vulnerability = irrigationType.includes('Canal') || irrigationType.includes('Drip') ? 0.2 : 0.5;
      climateYieldFactor += (rainDeficit / 100) * vulnerability;
    }
    if (soilMoisture < 0.35) {
      climateYieldFactor *= (0.75 + soilMoisture * 0.7); // Soil moisture stress penalty
    }

    climateYieldFactor = Math.max(0.45, Math.min(1.1, climateYieldFactor));
    const climateAdjustedYield = parseFloat((yieldResult.predictedYield * climateYieldFactor).toFixed(2));

    // Calculate Gross & Net Revenue
    const expectedProductionQuintals = climateAdjustedYield * landAcres * 10; // Convert tonnes/ha to total quintals
    const grossFarmRevenue = expectedProductionQuintals * apmcPrice;
    
    // Estimated Production Cost (~45% of gross revenue)
    const productionCost = grossFarmRevenue * 0.45;
    const netFarmRevenue = grossFarmRevenue - productionCost;

    // 3. Financial Debt Service Coverage Ratio (DSCR)
    const monthlyRate = (interestRate / 100) / 12;
    const emi = (loanAmount * monthlyRate * Math.pow(1 + monthlyRate, tenureMonths)) / 
                (Math.pow(1 + monthlyRate, tenureMonths) - 1);
    const totalAnnualObligation = emi * (tenureMonths > 12 ? 12 : tenureMonths);

    let rawDscr = totalAnnualObligation > 0 ? (netFarmRevenue / totalAnnualObligation) : 2.5;
    // Cap DSCR readout to max 10.0x for clean presentation
    const dscr = parseFloat(Math.min(10.0, Math.max(0.1, rawDscr)).toFixed(2));

    // 4. Climate Vulnerability Index (CVI) Stress Score
    let tempStress = Math.max(0, (temp - 30) * 0.08); // Temp > 30°C
    let rainStress = Math.max(0, (-rainDeficit) * 0.012); // Rainfall deficit
    let soilStress = Math.max(0, (0.45 - soilMoisture) * 0.6);
    let ndviDeficit = Math.max(0, (0.60 - ndvi) * 0.5);

    let totalClimateStress = tempStress + rainStress + soilStress + ndviDeficit;

    // Irrigation mitigates climate stress
    if (irrigationType.includes('Drip') || irrigationType.includes('Canal')) {
      totalClimateStress *= 0.45;
    }

    const climateRiskMultiplier = 1.0 + totalClimateStress;

    // 5. Clamped DSCR Impact on Score (-80 to +60 pts max)
    const dscrScoreBonus = Math.min(60, Math.max(-80, (dscr - 1.2) * 35));

    // 6. Dynamic Climate Credit Rating Score (300 to 900 scale)
    let rawScore = cibilScore - (totalClimateStress * 115) + dscrScoreBonus;
    const climateCreditScore = Math.round(Math.max(300, Math.min(900, rawScore)));

    // 7. Probability of Default (PD) Mathematically Aligned with Credit Score
    // Higher Score -> Lower Default Probability
    let pdClimate = Math.min(0.85, Math.max(0.015, Math.pow((900 - climateCreditScore) / 450, 1.8) * 0.25));
    if (climateCreditScore >= 720) {
      pdClimate = Math.min(0.065, pdClimate);
    }

    // 8. Loss Given Default (LGD) & Expected Loss (EL)
    const ltv = loanAmount / Math.max(loanAmount, collateralValue);
    const lgd = Math.max(0.15, Math.min(0.75, 0.40 * ltv));
    const expectedLoss = loanAmount * pdClimate * lgd;

    // 9. Consistent Decision Categorization
    let decision = 'HIGH RISK / REJECTED';
    let badgeClass = 'badge-danger';
    let decisionReason = 'High climate vulnerability and low forecasted revenue debt coverage ratio.';

    if (climateCreditScore >= 720) {
      decision = 'APPROVED';
      badgeClass = 'badge-success';
      decisionReason = 'Strong repayment capacity with low climate risk vulnerability.';
    } else if (climateCreditScore >= 610) {
      decision = 'CONDITIONAL APPROVAL';
      badgeClass = 'badge-warning';
      decisionReason = 'Approved subject to mandatory NABARD PM Fasal Bima Crop Insurance top-up & Drip Irrigation installation.';
    }

    return {
      applicantName: appData.applicantName || "Kisan Borrower",
      district: appData.district || "Vidarbha, Maharashtra",
      loanAmount: loanAmount,
      tenureMonths: tenureMonths,
      cibilScore: cibilScore,
      climateCreditScore: climateCreditScore,
      pdBasePct: parseFloat((pdClimate * 0.7 * 100).toFixed(2)),
      pdClimatePct: parseFloat((pdClimate * 100).toFixed(1)),
      lgdPct: parseFloat((lgd * 100).toFixed(1)),
      expectedLoss: Math.round(expectedLoss),
      predictedYield: climateAdjustedYield,
      baselineYield: yieldResult.predictedYield,
      grossFarmRevenue: Math.round(grossFarmRevenue),
      netFarmRevenue: Math.round(netFarmRevenue),
      annualEmi: Math.round(totalAnnualObligation),
      dscr: dscr,
      climateRiskMultiplier: parseFloat(climateRiskMultiplier.toFixed(2)),
      totalClimateStressScore: parseFloat(totalClimateStress.toFixed(3)),
      decision: decision,
      badgeClass: badgeClass,
      decisionReason: decisionReason,
      // Input copies for SHAP explainability
      inputs: { fert, temp, N, P, K, rainDeficit, soilMoisture, ndvi, irrigationType, cibilScore, dscr }
    };
  }
}

const riskEngine = new ClimateCreditRiskEngine();
