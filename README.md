# EcoTwin

EcoTwin is a local smart-manufacturing energy and process-optimization demonstration application. It combines a React dashboard with a FastAPI service, SQLite-backed machine and telemetry records, deterministic energy calculations, a saved prediction artifact, anomaly views, and scenario simulations.

> **Scope and evidence:** This repository is a demonstration and engineering prototype. Its included manufacturing records contain benchmark inputs, physically derived energy values, and synthetic factory context. It does not establish a deployed customer installation, site-metered energy performance, verified savings, or independently verified emissions reductions.

## Problem and intended users

The application is intended to help energy engineers, manufacturing/process engineers, maintenance planners, and sustainability analysts explore machine-level energy indicators, identify records that deviate from a chosen baseline, and examine operational scenarios. An operational recommendation or anomaly flag is a prompt for investigation—not proof of a mechanical fault or authorization to change a machine outside its approved operating envelope.

## Features and workflow

The React interface includes:

- Executive overview and daily energy trends.
- Machine fleet and machine detail views, including SEC and operating telemetry.
- Energy Intelligence machine comparison with cost and CO₂ estimates.
- Anomaly Center and operator resolution notes.
- Rule-based recommendations with evidence/provenance fields.
- What-If simulation, optional scenario saving, and an Impact view.
- Data Management summaries and provenance tiers. File import is not implemented.
- Settings for the browser-local Dark/Light preference, energy assumptions, and a separately confirmed, narrowly scoped demo-anomaly reset.

A typical demonstration flow is: inspect the overview → select a machine → review energy/anomaly context → run a What-If scenario → save only if desired → review the projected impact and its assumptions. A What-If projection is not a measured or verified outcome.

## Architecture and technology

- **Frontend:** React, TypeScript, Vite, Tailwind CSS, Apache ECharts, React Router, and TanStack Query.
- **Backend:** FastAPI, Pydantic, SQLAlchemy, pandas, NumPy, and scikit-learn/XGBoost-related model support.
- **Persistence:** SQLite by default; SQLAlchemy reads `DATABASE_URL` at process startup.
- **Model artifact:** `models/best_energy_model.joblib`; the application loads it but does not train or retrain it during normal startup.
- **Additional interface:** `dashboard/app.py` also retains legacy server-rendered dashboard routes/templates alongside the React SPA.

See [Technical Documentation](docs/TECHNICAL_DOCUMENTATION.md) for module responsibilities, API endpoints, database entities, formulas, model limitations, and verification guidance.

## Prerequisites

The project environment used for validation had Python 3.12, Node.js 24, and npm 11. Use a Python version supported by the packages in `requirements.txt` and a Node version supported by the Vite toolchain. The Python requirements file is not a lockfile; `frontend/package-lock.json` is the frontend lockfile.

## Install and run locally (Windows PowerShell)

Run commands from the repository root unless stated otherwise. Use a **new, isolated database path** for a fresh demo; do not point the seed command at a database containing user data.

```powershell
# Python environment and backend dependencies
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

# Create and seed a separate demo database (set before Python imports the DB module)
$env:DATABASE_URL = "sqlite:///./ecotwin_demo.db"
python -m src.db.seed

# Start the API in this terminal
python -m uvicorn dashboard.app:app --reload --host 127.0.0.1 --port 8000
```

In a second terminal:

```powershell
Set-Location frontend
npm ci
npm run dev -- --host 127.0.0.1
```

Open the Vite URL printed by the command (normally `http://127.0.0.1:5173`). The Vite development server proxies `/api` to `http://localhost:8000`. The React API client defaults to `/api`; `VITE_API_BASE_URL` can override that request prefix when a different deployment topology is deliberately configured.

At FastAPI startup, `src/db/bootstrap.py` creates missing tables and seeds the demo dataset only when all application data tables are empty. That first-time seed reads the processed CSV; existing data is preserved without automatic supplementation. The saved model and its legacy analytics dataframe are loaded only if a retained model-backed dashboard route is requested; the active database-backed React API does not load the ML artifact at startup. Keep the processed CSV and model artifact available for the seed/legacy paths. The seed utility does not delete records and is not a migration or repair tool for a partially populated database.

The root `ecotwin.db` is local working data and is intentionally not included in the portable source ZIP. Protect and back it up separately according to local data-handling requirements.

### Configuration

- `DATABASE_URL`: SQLAlchemy URL; default `sqlite:///./ecotwin.db`, relative to the process working directory. Set it before launching Python. SQLite is the configured and tested default. Other database URLs require a compatible SQLAlchemy driver and have not been validated by this project.
- `VITE_API_BASE_URL`: optional frontend API prefix; default `/api`. The development proxy target is configured in `frontend/vite.config.ts`.
- `FRONTEND_ORIGINS`: comma-separated exact browser origins allowed by FastAPI CORS, for example `https://ecotwin-frontend.onrender.com`. Do not include paths or wildcard origins.
- No API key is required for the documented local workflow. Do not place credentials in source control or in the portable source package.

## API documentation

With the backend running, FastAPI serves the generated OpenAPI schema at `/openapi.json` and interactive docs at `/docs`. The versioned API is mounted under `/api/v1`. Primary operations include:

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `GET` | `/api/v1/health` | Health/status response. |
| `GET` | `/api/v1/overview` | Facility and fleet summary, trend, cost, CO₂ estimate, provenance. |
| `GET` | `/api/v1/machines` | Machine list. |
| `GET` | `/api/v1/machines/{machine_id}` | Machine details, operating statistics, readings, anomaly records. |
| `GET` | `/api/v1/telemetry` | Filtered/paginated telemetry. |
| `GET` | `/api/v1/anomalies` | Filtered/paginated anomaly records. |
| `POST` | `/api/v1/anomalies/{anomaly_id}/resolve` | Store an operator resolution note. |
| `GET` | `/api/v1/energy/overview` | Energy overview. |
| `GET` | `/api/v1/energy/machine-comparison` | Machine SEC, energy, cost, and CO₂ comparison. |
| `GET`, `PUT` | `/api/v1/config` | Read/update persisted analysis assumptions. |
| `GET` | `/api/v1/recommendations` | Evidence-oriented recommendations. |
| `POST` | `/api/v1/whatif/simulate` | Run a non-persistent What-If simulation. |
| `POST` | `/api/v1/whatif/save` | Persist a named scenario. |
| `GET` | `/api/v1/whatif/scenarios` | List saved scenarios. |
| `POST` | `/api/v1/demo-data/reset` | Confirmed reset of whitelisted demo anomaly resolution flags only. |

For exact query and body schemas, consult generated OpenAPI rather than relying on this summary.

## Calculations and scientific limitations

- **Derived energy:** raw AI4I 2020 data does not contain electrical kWh meter readings. The processing code derives mechanical power as `torque × rotational_speed × 2π / 60`, derives electrical power using a nominal motor-efficiency assumption, maps product type to an assumed cycle time, then calculates `energy_kwh = electrical_power_watts × cycle_time_hours / 1000`. The default efficiency for this path is 0.85. These values are analytical derivations, not measured site energy.
- **SEC:** calculated energy per recorded part, in `kWh/part`; aggregates use total energy divided by the associated part/reading count. It is not interchangeable with `kWh/kg`.
- **Cost:** energy multiplied by the configured base tariff (`INR/kWh`) where used. Scenario-specific time-of-use assumptions are modeled separately; not every page uses the same tariff treatment.
- **CO₂:** energy multiplied by the configured grid factor (`kg CO₂/kWh`), then divided by 1,000 for tonnes. This is an estimate using an assumed factor, not a verified emissions inventory.
- **Synthetic context:** machine assignment, energy penalties/drift, shift context, idle-time values, ambient context, and some tariffs are demonstration data generated by augmentation code. Do not treat them as plant observations.
- **Predictions, anomaly residuals, and recommendations** are model outputs or heuristic indicators. They do not establish causation, a mechanical fault, or realized savings. The saved model artifact contains training metadata; this repository does not claim an independently verified holdout result.
- **What-If and Impact values** are projections under stated baseline, engineering, production, tariff, and emissions assumptions. A simulated/projected result must never be presented as verified savings.

See the technical guide for detailed formulas, the saved model feature list, known inconsistencies, and measurement-and-verification requirements.

## Tests and quality checks

From the repository root, using the project virtual environment:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Frontend checks:

```powershell
Set-Location frontend
npx tsc --noEmit --project tsconfig.app.json
npm run lint
npm run build
```

There is no frontend unit-test script configured in `frontend/package.json`. For API tests that exercise database mutations, point `DATABASE_URL` at a disposable, seeded test database; never use the live working database for reset or mutation testing.

## Demo Data reset

Settings → **Reset Demo Data** asks for explicit confirmation. `POST /api/v1/demo-data/reset` requires `{"confirm": true}` and only reopens the specifically fingerprinted original demo anomaly events. Before a changing reset, the service creates and integrity-checks a SQLite backup. It does not create/delete anomaly or telemetry records, rewrite measurements, or reset settings/scenarios/models. A fingerprint mismatch fails closed. The operation does not restore arbitrary operator resolution states; changes to the whitelisted demo resolution flags are intentionally reverted. Test reset behavior only with isolated database fixtures.

## Deployment considerations

`render.yaml` defines a separate free-tier FastAPI web service and Vite static site. It sets the API start command, frontend build, `FRONTEND_ORIGINS`, and `VITE_API_BASE_URL`; confirm the assigned Render hostnames match those values if names/domains change. The API uses SQLite at `/tmp/ecotwin.db` on Render Free. That filesystem is ephemeral: database contents can be lost on restart, redeploy, or instance replacement, so this configuration is suitable for a demonstration rather than durable multi-user storage. No deployment has been performed.

Render configuration does not add authentication, authorization, durable database backups, migrations, or production-grade observability. Do not expose sensitive or customer data. Before operational use, complete a security review and data-governance plan, validate tariff/emissions assumptions for the actual jurisdiction and period, and implement a documented measurement-and-verification protocol before reporting realized impact.
