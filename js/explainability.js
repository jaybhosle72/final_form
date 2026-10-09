// NABARD FIN-03 SHAP-style Explainability & Risk Driver Attribution Engine

class RiskExplainabilityEngine {
  /**
   * Generates SHAP attribution breakdown & qualitative risk analysis report.
   * @param {Object} riskResult Output from ClimateCreditRiskEngine
   * @returns {Object} SHAP feature contributions and risk mitigation recommendations
   */
  generateExplanation(riskResult) {
    const inputs = riskResult.inputs;
    const baseScore = 700; // Reference baseline score

    const shapValues = [];

    // 1. CIBIL Financial History Driver
    const cibilContrib = inputs.cibilScore - 700;
    shapValues.push({
      feature: "CIBIL / Credit Record",
      value: inputs.cibilScore,
      unit: "score",
      impactPoints: cibilContrib,
      type: cibilContrib >= 0 ? "positive" : "negative",
      description: cibilContrib >= 0 ? "Solid past financial repayment history." : "Sub-optimal historical financial record."
    });

    // 2. Temperature Heat Stress Driver
    let tempImpact = 0;
    if (inputs.temp > 30) {
      tempImpact = Math.round(- (inputs.temp - 30) * 14.5);
    } else {
      tempImpact = Math.round((30 - inputs.temp) * 3.5);
    }
    shapValues.push({
      feature: "Temperature / Heat Stress",
      value: `${inputs.temp}°C`,
      unit: "°C",
      impactPoints: tempImpact,
      type: tempImpact >= 0 ? "positive" : "negative",
      description: inputs.temp > 32 ? `Elevated heat stress (${inputs.temp}°C) causes crop yield reduction.` : "Optimal temperature range for high productivity."
    });

    // 3. Rainfall Anomaly Driver
    let rainImpact = 0;
    if (inputs.rainDeficit < 0) {
      rainImpact = Math.round(inputs.rainDeficit * 2.8); // e.g. -25% -> -70 points
    } else {
      rainImpact = Math.round(Math.min(40, inputs.rainDeficit * 1.5));
    }
    shapValues.push({
      feature: "Monsoon Rainfall Anomaly",
      value: `${inputs.rainDeficit >= 0 ? '+' : ''}${inputs.rainDeficit}%`,
      unit: "%",
      impactPoints: rainImpact,
      type: rainImpact >= 0 ? "positive" : "negative",
      description: inputs.rainDeficit < -15 ? `Severe rainfall deficit (${inputs.rainDeficit}%) increases drought risk.` : "Adequate monsoon rainfall coverage."
    });

    // 4. Irrigation System Buffer Driver
    let irrigationImpact = 0;
    if (inputs.irrigationType.includes('Drip')) {
      irrigationImpact = +65;
    } else if (inputs.irrigationType.includes('Canal') || inputs.irrigationType.includes('Tube-well')) {
      irrigationImpact = +45;
    } else {
      irrigationImpact = -35; // Purely Rainfed
    }
    shapValues.push({
      feature: "Irrigation Infrastructure",
      value: inputs.irrigationType,
      unit: "type",
      impactPoints: irrigationImpact,
      type: irrigationImpact >= 0 ? "positive" : "negative",
      description: inputs.irrigationType === 'Rainfed' ? "High vulnerability due to lack of artificial irrigation." : "Irrigation infrastructure provides strong climate risk buffer."
    });

    // 5. N-P-K & Fertilizer Optimization Driver
    let fertBalanceScore = Math.round((inputs.fert - 70) * 0.8 + (inputs.N - 70) * 0.5 + (inputs.P - 20) * 1.2);
    shapValues.push({
      feature: "Soil N-P-K & Fertilizer",
      value: `${inputs.fert} kg/ha (N:${inputs.N}, P:${inputs.P}, K:${inputs.K})`,
      unit: "ratio",
      impactPoints: fertBalanceScore,
      type: fertBalanceScore >= 0 ? "positive" : "negative",
      description: fertBalanceScore >= 0 ? "Optimal soil nutrition supports high crop productivity." : "Low nutrient application limits yield capability."
    });

    // 6. Debt Service Coverage Ratio (DSCR)
    let dscrImpact = Math.round((riskResult.dscr - 1.2) * 40);
    shapValues.push({
      feature: "Debt Service Coverage (DSCR)",
      value: `${riskResult.dscr}x`,
      unit: "ratio",
      impactPoints: dscrImpact,
      type: dscrImpact >= 0 ? "positive" : "negative",
      description: riskResult.dscr >= 1.25 ? "Comfortable cashflow margin to service loan EMI." : "Tight farm revenue margin to service debt."
    });

    // Actionable Recommendations for NABARD Credit Officers & Farmers
    const recommendations = [];
    if (inputs.irrigationType === 'Rainfed') {
      recommendations.push("🌱 **Mitigation Alert**: Grant 30% top-up loan micro-subsidy for installing Solar Drip Irrigation, which will boost credit rating score by +65 pts.");
    }
    if (inputs.rainDeficit < -20 || inputs.temp > 33) {
      recommendations.push("☂️ **Climate Insurance Requirement**: Mandatory enrollment in Pradhan Mantri Fasal Bima Yojana (PMFBY) Weather-Based Crop Insurance to cover default risk.");
    }
    if (inputs.fert < 65 || inputs.P < 20) {
      recommendations.push("🧪 **Agronomic Support**: Recommend Soil Health Card test & balanced N-P-K fertilizer application to raise harvest yield from " + riskResult.predictedYield + " to " + (riskResult.predictedYield * 1.15).toFixed(1) + " tonnes/ha.");
    }

    if (recommendations.length === 0) {
      recommendations.push("✅ **Optimal Profile**: Borrower exhibits low climate exposure and high repayment security. Approved for standard interest rate discount of -0.50%.");
    }

    return {
      shapValues: shapValues,
      totalCalculatedScore: riskResult.climateCreditScore,
      recommendations: recommendations
    };
  }
}

const explainabilityEngine = new RiskExplainabilityEngine();
