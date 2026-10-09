# Climate-Aware Credit Risk Assessment for Agriculture — Base Foundation

Institutional web application foundation for the **NABARD Climate-Aware Credit Risk Assessment** project.

This repository implements **Phase 1 (Base Foundation)**. It establishes the core website layout, shared navigation, agricultural finance design system, dataset organization, and informative module placeholders.

---

## 📋 Project Overview & Modules

The application is structured into 4 primary views accessible via hash routing:

1. **Dashboard (`#/dashboard`)**:
   - Project title and institutional purpose.
   - High-level overview of project modules.
   - Foundational layout for future portfolio metrics.

2. **Loan Records (`#/loans`)**:
   - Layout for agricultural loan application records.
   - Placeholder section for the 100-farmer synthetic dataset.
   - Explicit disclaimer regarding synthetic data usage.

3. **Climate Data (`#/climate`)**:
   - Overview of planned climate and agronomic indicators.
   - Descriptions of Sentinel-2 NDVI satellite imagery, heatwave forecasts, monsoon rainfall anomalies, and soil moisture telemetry.

4. **Risk Assessment (`#/risk`)**:
   - Framework for future credit risk assessment engines.
   - Descriptions of climate-adjusted credit scoring (300-900), XGBoost yield forecasting, SHAP explainability (XAI), and climate stress testing.

---

## 🛠️ Technology Stack

- **Frontend Core**: Vanilla HTML5, CSS3, JavaScript (ES6+).
- **Icons**: Lucide Icons.
- **Routing**: Client-side hash router (`#/dashboard`, `#/loans`, `#/climate`, `#/risk`) supporting browser back/forward navigation.
- **Styling**: Custom Agricultural Finance Design System (White background, Deep Teal `#0d9488` & Aqua Cyan `#06b6d4` accents, dark readable text `#0f172a`, responsive flex/grid layouts).

---

## 📁 Folder Structure

```
finalform/
├── index.html              # Main HTML entry point & page layout
├── css/
│   └── styles.css          # Agricultural-finance design system & responsive styles
├── js/
│   ├── app.js              # Active Phase 1 client router & navigation controller
│   ├── data.js             # Preserved dataset reference definitions
│   ├── risk_engine.js      # Preserved risk assessment engine (Phase 3)
│   ├── yield_model.js      # Preserved ML yield prediction models (Phase 3)
│   ├── explainability.js   # Preserved SHAP explainability engine (Phase 3)
│   └── satellite_api.js    # Preserved satellite telemetry connectors (Phase 2)
├── data/
│   └── synthetic_agricultural_loan_repayment_100_farmers.csv  # Synthetic dataset
├── backend/                # Preserved FastAPI python backend (Phase 3)
└── README.md               # Project documentation and setup guide
```

---

## 📊 Dataset Disclaimer

The dataset file `data/synthetic_agricultural_loan_repayment_100_farmers.csv` is stored in the project structure for future development.

> **IMPORTANT DISCLAIMER**:
> This dataset contains **synthetic demonstration data** generated for testing purposes only. It does **NOT** contain actual farmer, bank, or NABARD loan records. Do not process, analyze, or interpret these records as real financial data.

---

## 🚀 How to Run the Application

Because this application uses standard static Web standards (HTML/CSS/JS), it can be served using any standard HTTP server.

### Option 1: Python HTTP Server (Recommended)
From the `finalform/` directory, run:
```bash
python -m http.server 8080
```
Then open your browser and navigate to:
[http://localhost:8080](http://localhost:8080)

### Option 2: Node.js `serve`
From the `finalform/` directory, run:
```bash
npx serve .
```

### Option 3: VS Code Live Server
Right-click `index.html` in VS Code and select **"Open with Live Server"**.

---

## 🔒 Phase 1 Scope Restrictions

In accordance with Phase 1 requirements:
- **NO** predictive machine learning models are executed.
- **NO** live credit scores or default probabilities are calculated.
- **NO** external weather or satellite APIs are called.
- **NO** fabricated data metrics or loan approval decisions are generated.
- All future-phase code files are safely preserved in the codebase without executing in the active UI.
