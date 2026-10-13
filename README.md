# EcoTwin — Intelligent Energy & Process Optimization for Smart Manufacturing

> **Yuva Yodha Energy Tech Hackathon 2026 | Schneider Electric | Smart Manufacturing Track**

<div align="center">

⚡ *Predict energy. Detect waste. Explain causes. Optimize decisions. Prove impact.* ⚡

</div>

---

## 🎯 The Problem

Indian manufacturing SMEs waste **20–40% more energy per unit** than achievable benchmarks, yet lack visibility into where, why, or how to fix it. They track energy only as a lump-sum monthly bill — not as a controllable performance metric.

## 💡 The Solution

**EcoTwin** is a software-first decision support system that transforms fragmented operational data into explainable energy intelligence:

| Step | Question | EcoTwin's Answer |
|------|----------|-----------------|
| 1 | What's happening? | Real-time energy monitoring with SEC (kWh/part) tracking |
| 2 | Is it abnormal? | Context-aware anomaly detection (high energy at low production ≠ high energy at high production) |
| 3 | Why? | SHAP-based explainability + rule-based diagnostic codes |
| 4 | What should I do? | Prioritized, constraint-aware recommendations |
| 5 | What will happen? | Interactive What-If simulator with instant impact preview |
| 6 | How much will I save? | Quantified impact: kWh, ₹, kg CO₂ |

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    ECOTWIN PIPELINE                      │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  Raw Data ──→ Processing ──→ Feature Engineering         │
│       │                           │                      │
│       ▼                           ▼                      │
│  Energy Prediction ◄── XGBoost (R²=0.971)                │
│       │                                                  │
│       ▼                                                  │
│  Anomaly Detection ◄── Residual + Isolation Forest       │
│       │                                                  │
│       ▼                                                  │
│  Explainability ◄── SHAP + Diagnostic Codes              │
│       │                                                  │
│       ▼                                                  │
│  Recommendations ◄── Priority scoring + Constraints      │
│       │                                                  │
│       ▼                                                  │
│  What-If Simulator ──→ Impact Calculator                 │
│       │                   (kWh, ₹, CO₂)                  │
│       ▼                                                  │
│  Interactive Dashboard (Streamlit)                        │
└─────────────────────────────────────────────────────────┘
```

## 📊 ML Model Performance

| Model | Val MAE (kWh) | Val R² | Test R² | MAPE |
|-------|:---:|:---:|:---:|:---:|
| Ridge Regression | 0.0236 | 0.958 | — | 8.3% |
| Random Forest | 0.0186 | 0.979 | — | 6.0% |
| **XGBoost** ⭐ | **0.0184** | **0.980** | **0.971** | **6.2%** |
| LightGBM | 0.0185 | 0.980 | — | 6.0% |

## 🏃 Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run the dashboard
streamlit run dashboard/app.py
```

## 📁 Project Structure

```
ecotwin/
├── data/
│   ├── raw/                  # Original datasets (AI4I 2020, Steel Industry)
│   ├── processed/            # Feature-engineered data
│   └── synthetic/            # Synthetic augmentation documentation
├── src/
│   ├── data/                 # Loading, processing, synthetic augmentation
│   ├── models/               # Prediction, anomaly detection, equipment intelligence
│   ├── explainability/       # SHAP engine, diagnostic reason codes
│   ├── optimization/         # What-If simulator, recommendations, impact calculator
│   └── utils/                # Constants, validators
├── dashboard/
│   └── app.py                # Streamlit multi-page dashboard
├── models/                   # Saved trained model artifacts
├── docs/                     # Experiment log, decision log
├── tests/                    # Unit tests
├── requirements.txt
└── README.md
```

## 📐 Data Transparency

| Data Source | Type | License | Usage |
|-------------|------|---------|-------|
| AI4I 2020 Predictive Maintenance (UCI) | Real | CC BY 4.0 | Core: 10,000 manufactured parts with process telemetry |
| Steel Industry Energy (UCI) | Real | CC BY 4.0 | Supplementary: factory-level energy patterns |
| Factory context (shift, tariff, maintenance) | **Synthetic** | N/A | Augmentation — clearly labeled, seeded for reproducibility |

### Key Constants (Sources)
- Grid emission factor: **0.716 kg CO₂/kWh** — CEA India CO₂ Baseline Database v19
- Industrial tariff: **₹8.50/kWh** — Maharashtra MSEDCL HT-I Industrial average
- Peak/off-peak multipliers: **±20%** — State ToD regulations

## 🔧 Technology Stack

| Layer | Technology |
|-------|-----------|
| Language | Python 3.10+ |
| ML | Scikit-learn, XGBoost, LightGBM |
| Explainability | SHAP (TreeExplainer) |
| Visualization | Plotly |
| Dashboard | Streamlit |
| Data | Pandas, NumPy |

## 🌍 Impact Potential

For a typical Indian injection molding SME (4 machines, 800 parts/day):
- **Energy reduction:** 10–15% SEC improvement achievable
- **Cost saving:** ₹3–5 lakh/year in reduced electricity bills
- **CO₂ reduction:** 2–4 tonnes CO₂/year
- **Payback:** Software-only deployment — no hardware CAPEX required

## ⚖️ Honest Limitations

1. Model trained on semi-synthetic data; real-world deployment requires factory-specific calibration
2. Anomaly explanations are probabilistic hypotheses, not definitive root causes
3. What-If predictions degrade for parameter combinations far outside training distribution
4. Single manufacturing process type (machining); extending to other processes requires new training data
5. No real-time IoT integration in current prototype — operates on batch/historical data

---

*Built by Saish for the Yuva Yodha Energy Tech Hackathon 2026 — Schneider Electric*
