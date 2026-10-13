# EcoTwin — Intelligent Energy & Process Optimization for Smart Manufacturing

> **Yuva Yodha Energy Tech Hackathon 2026 | Schneider Electric | Smart Manufacturing Track**

<div align="center">

⚡ *Predict baseline energy. Detect operational waste. Explain root causes. Optimize decisions. Prove impact.* ⚡

</div>

---

## 🎯 The Problem

Indian manufacturing SMEs waste **20–40% more energy per unit** than achievable benchmarks, yet lack visibility into where, why, or how to fix it. They track energy only as a lump-sum monthly bill — not as a controllable performance metric.

## 💡 The Solution

**EcoTwin** is an explainable decision support system that transforms operational telemetry into explainable energy intelligence:

```
OBSERVE → UNDERSTAND → PREDICT → DETECT → DIAGNOSE → OPTIMIZE → PROVE
```

| Step | Question | EcoTwin's Answer | Data Provenance Tier |
|:---:|:---|:---|:---:|
| 1 | What's happening? | Real-time energy monitoring with SEC (kWh/part) tracking | Tier 1 (Sensors) & Tier 2 (Derived Physics) |
| 2 | What is expected? | First-principles analytical baseline & machine-learning models | Tier 2 (Analytical) & Tier 4 (Model Baseline) |
| 3 | Is it abnormal? | Context-aware residual SPC ($|Z| \ge 2.0$) & Isolation Forest | Tier 4 (Model Output) |
| 4 | Why? | TreeSHAP local attribution + heuristic diagnostic codes | Tier 4 (Diagnostics) |
| 5 | What should I do? | Prioritized, constraint-aware operational recommendations | Optimization Engine |
| 6 | What will happen? | Coupled kinematic What-If sandbox with standardized OOD checks | Tier 5 (Simulation Scenario) |
| 7 | How much will I save? | Quantified impact: kWh, ₹, kg CO₂ based on CEA & MSEDCL benchmarks | Impact Calculator |

---

## 📐 Data Provenance & Scientific Transparency

EcoTwin strictly separates empirical observations from engineering derivations:

| Tier | Name | Description | Source / Variables |
|:---:|:---|:---|:---|
| **Tier 1** | **Sensor Measurements** | Empirical telemetry directly from physical sensors. | Rotational speed (rpm), Torque (Nm), Tool wear (min), Air temp (K), Process temp (K), Failure flags. |
| **Tier 2** | **Physically Derived** | Quantities calculated using first-principles formulas. | $P_{\text{mech}} = \tau \cdot \omega$, $P_{\text{elec}} = P_{\text{mech}} / 0.85$, $E = P_{\text{elec}} \cdot t_{\text{cycle}} / 1000$, $\text{SEC} = E / 1.0$. |
| **Tier 3** | **Calibrated Context** | Synthesized factory context for multi-machine simulation. | Machine IDs (M-01 to M-04), 2024 timeline, Indian 3-shift calendar, MSEDCL tariffs. |
| **Tier 4** | **Model Outputs** | Statistical baselines and anomaly residual scores. | Residual $Z$-score, severity (watch/warning/critical), TreeSHAP feature contributions. |
| **Tier 5** | **Simulated Scenarios** | What-If sandbox outcomes constrained by physical limits. | Projected energy, cost (₹), carbon ($\text{kg CO}_2$), Standardized OOD distance. |

---

## 📊 Model & Baseline Evaluation (Non-Leaky Features)

Evaluated on 2,000 unseen holdout parts (80/20 train/test split) using clean operational features (no algebraic target components):

| Model / Approach | Test MAE (kWh) | Test MAPE | Test $R^2$ | Notes |
|:---|:---:|:---:|:---:|:---|
| **Analytical Physics Baseline** | **0.0207** | **6.63%** | **0.9644** | **Zero-parameter first principles:** $P = \tau \cdot \omega / 0.85$, $E = P \cdot t$. Explains 96.4% of variance directly. |
| **Product Type Mean Baseline** | 0.0430 | 15.33% | 0.8602 | Naive class-average baseline (L, M, H). |
| **Ridge Regression** | 0.0248 | 8.98% | 0.9548 | Linear model on non-leaky operational features. |
| **Random Forest** | 0.0155 | 5.13% | 0.9841 | Captures non-linear tool wear and shift multipliers. |
| **XGBoost** | 0.0158 | 5.26% | 0.9828 | Gradient boosted trees capturing machine drift and shift penalties. |

---

## 🏃 Quick Start & Local Execution

### 1. Environment Setup

```bash
# Clone and enter workspace
cd ecotwin

# Create and activate virtual environment (optional)
python -m venv venv
# Windows:
.\venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Database Configuration & Seeding

EcoTwin features pluggable persistence:
- **Default:** SQLite (`sqlite:///./ecotwin.db`) for zero-dependency local execution.
- **PostgreSQL:** Set `DATABASE_URL=postgresql://user:password@localhost:5432/ecotwin` in `.env`.

```bash
# Initialize database tables and seed with 10,000 telemetry records:
python -c "from src.db.seed import seed_database; print(seed_database())"
```

### 3. Start the FastAPI Server

```bash
python -m uvicorn dashboard.app:app --reload --port 8000
```

Access:
- **Interactive OpenAPI Docs:** http://localhost:8000/docs
- **ReDoc Documentation:** http://localhost:8000/redoc
- **API Health Check:** http://localhost:8000/api/v1/health

### 4. Run Automated Tests

```bash
python -m pytest -v
```

All 33 automated tests run against an isolated test database with zero external dependencies.

---

## 🔌 REST API Endpoints (v1)

| Router | Method | Endpoint | Description |
|:---|:---:|:---|:---|
| **Health** | `GET` | `/api/v1/health` | Operational health and database persistence status |
| **Overview** | `GET` | `/api/v1/overview` | Executive Command Center KPIs, fleet health, and daily trends |
| **Machines** | `GET` | `/api/v1/machines` | List all monitored machines (M-01 to M-04) |
| **Machines** | `GET` | `/api/v1/machines/{id}` | Machine Digital Twin state, gauges, and recent readings |
| **Telemetry** | `GET` | `/api/v1/telemetry` | Paginated operational telemetry with provenance tiers |
| **Anomalies** | `GET` | `/api/v1/anomalies` | Query logged energy anomalies and diagnostic codes |
| **Anomalies** | `POST` | `/api/v1/anomalies/{id}/resolve`| Mark anomaly as resolved with operator notes |
| **What-If** | `POST` | `/api/v1/whatif/simulate` | Coupled physics simulation with OOD guardrails |
| **What-If** | `POST` | `/api/v1/whatif/save` | Save scenario for M&V verification |
| **What-If** | `GET` | `/api/v1/whatif/scenarios` | List saved scenarios |
| **Config** | `GET` | `/api/v1/config` | View active tariffs and emission factors |
| **Config** | `PUT` | `/api/v1/config` | Update configurable tariffs and grid factors |

---

## 📁 Project Structure

```
ecotwin/
├── data/
│   ├── raw/                  # Original datasets (AI4I 2020, Steel Industry)
│   ├── processed/            # Feature-engineered dataset
│   └── synthetic/            # Synthetic augmentation documentation
├── src/
│   ├── api/v1/               # Modular FastAPI REST routers
│   ├── db/                   # SQLAlchemy 2.x engine, models, and seeder
│   ├── schemas/              # Pydantic v2 request/response contracts
│   ├── services/             # Decoupled business logic services
│   ├── data/                 # Processing, units, analytical derivations
│   ├── models/               # Anomaly detection & leak-free predictors
│   ├── explainability/       # TreeSHAP engine, diagnostic codes
│   ├── optimization/         # What-If simulator, recommendations
│   └── utils/                # Physical constants, validators, tiers
├── dashboard/
│   └── app.py                # FastAPI application mounting v1 API
├── docs/
│   └── experiment_log.csv    # Empirical validation logs
├── tests/
│   ├── test_api.py           # Legacy endpoint regression tests
│   ├── test_data_integrity.py# Milestone 1 provenance & leakage tests
│   ├── test_database_and_api.py # Milestone 2 DB & API v1 integration tests
│   └── test_utils.py         # Physics & unit tests
├── requirements.txt
└── README.md
```

---

## ⚖️ Honest Limitations & Scientific Integrity

1. **Analytical vs. Measured Energy:** Electrical energy in the discrete machining module is derived via first-principles kinematics and motor efficiency ($\eta = 0.85$), not direct IoT smart meter hardware.
2. **Standardized OOD Guardrails:** The What-If simulator flags inputs outside supported bounds ($d_{\text{OOD}} > 2.0$), but does not replace professional structural tooling calculations.
3. **Probabilistic Explanations:** TreeSHAP attributions indicate feature correlation with anomalies, requiring operator verification before mechanical teardown.
4. **Regulatory Standards:** Emission factors ($0.716\,\text{kg CO}_2/\text{kWh}$) reflect CEA India National Grid v19.0; tariffs reflect Maharashtra MSEDCL HT-I industrial benchmarks.
