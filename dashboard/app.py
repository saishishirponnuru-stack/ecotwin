"""
EcoTwin Dashboard — FastAPI Application
=========================================
Professional industrial energy intelligence dashboard built with:
FastAPI + Jinja2 + Tailwind CSS + Alpine.js + Plotly.js

Run: python -m uvicorn dashboard.app:app --reload --port 8000
"""

import os
import sys
import json
import numpy as np
import pandas as pd
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

# Add project root to path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from src.models.predictor import EnergyPredictor
from src.optimization.impact import ImpactCalculator
from src.optimization.recommender import RecommendationEngine
from src.utils.constants import GRID_EMISSION_FACTOR, BASE_TARIFF_INR, MACHINE_IDS
from src.api.v1 import api_v1_router
from src.db.database import init_db

# ─── FastAPI App ─────────────────────────────────────────────────────────────
app = FastAPI(
    title="EcoTwin API",
    description="Industrial Energy Intelligence REST API",
    version="0.2.0",
)

# Mount REST API v1 routers
app.include_router(api_v1_router)

DASHBOARD_DIR = os.path.dirname(os.path.abspath(__file__))
app.mount("/static", StaticFiles(directory=os.path.join(DASHBOARD_DIR, "static")), name="static")
templates = Jinja2Templates(directory=os.path.join(DASHBOARD_DIR, "templates"))



# ─── Data & Model Loading ────────────────────────────────────────────────────
def load_all_data():
    """Load processed data and trained model."""
    data_path = os.path.join(PROJECT_ROOT, "data", "processed", "manufacturing_data.csv")
    df = pd.read_csv(data_path)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df["product_type_encoded"] = df["product_type"].map({"L": 0, "M": 1, "H": 2})
    df["shift_encoded"] = df["shift"].map({"Day": 0, "Evening": 1, "Night": 2})

    model_path = os.path.join(PROJECT_ROOT, "models", "best_energy_model.joblib")
    model = EnergyPredictor.load(model_path)

    features = [
        "power_watts", "rotational_speed_rpm", "torque_nm", "tool_wear_min",
        "air_temp_k", "process_temp_k", "cycle_time_minutes", "idle_time_seconds",
        "product_type_encoded", "shift_encoded", "maintenance_days_since", "ambient_temperature",
    ]
    available = [f for f in features if f in df.columns]

    predictions = model.predict(df[available])
    df["predicted_kwh"] = predictions
    df["residual_kwh"] = df["energy_kwh"] - predictions
    df["deviation_pct"] = np.where(predictions > 0, (df["residual_kwh"] / predictions) * 100, 0)

    median_r = np.median(df["residual_kwh"])
    mad = np.median(np.abs(df["residual_kwh"] - median_r))
    sigma = 1.4826 * mad if mad > 0 else df["residual_kwh"].std()
    df["z_score"] = (df["residual_kwh"] - median_r) / sigma if sigma > 0 else 0

    df["severity"] = np.where(
        np.abs(df["z_score"]) >= 3.0, "critical",
        np.where(np.abs(df["z_score"]) >= 2.0, "warning",
                 np.where(np.abs(df["z_score"]) >= 1.5, "watch", "normal")))
    df["is_anomaly"] = np.abs(df["z_score"]) >= 2.0

    return df, model, features


# Load on startup
DF, MODEL, FEATURES = load_all_data()


# ─── Template Routes (HTML Pages) ────────────────────────────────────────────
@app.get("/", response_class=HTMLResponse)
async def overview_page(request: Request):
    """Factory Overview page."""
    avg_sec = float(DF["sec_kwh_per_part"].mean())
    total_energy = float(DF["energy_kwh"].sum())
    anomaly_count = int(DF["is_anomaly"].sum())
    normal_pct = float((DF["severity"] == "normal").mean() * 100)
    efficiency_score = int(min(normal_pct, 99))
    co2_tonnes = total_energy * GRID_EMISSION_FACTOR / 1000

    # Machine performance
    machine_perf = []
    for mid in MACHINE_IDS:
        mdata = DF[DF["machine_id"] == mid]
        avg_dev = float(mdata["deviation_pct"].mean())
        eff = max(0, min(100, 100 - abs(avg_dev)))
        anom = int(mdata["is_anomaly"].sum())
        machine_perf.append({
            "id": mid, "efficiency": round(eff, 1),
            "avg_sec": round(float(mdata["sec_kwh_per_part"].mean()), 4),
            "anomalies": anom, "avg_deviation": round(avg_dev, 1),
        })

    # Active alerts (top anomalous machines)
    alerts = []
    anomaly_df = DF[DF["is_anomaly"]]
    if not anomaly_df.empty:
        for mid in anomaly_df["machine_id"].unique():
            m_anom = anomaly_df[anomaly_df["machine_id"] == mid]
            excess = float(m_anom["residual_kwh"][m_anom["residual_kwh"] > 0].sum())
            alerts.append({
                "machine_id": mid,
                "count": int(len(m_anom)),
                "avg_deviation": round(float(m_anom["deviation_pct"].mean()), 1),
                "potential_saving_inr": round(excess * BASE_TARIFF_INR, 0),
            })
        alerts.sort(key=lambda x: x["potential_saving_inr"], reverse=True)

    # Daily energy trend (actual vs predicted)
    daily = DF.groupby(DF["timestamp"].dt.date).agg(
        actual=("energy_kwh", "sum"), predicted=("predicted_kwh", "sum")
    ).reset_index()
    daily_chart = {
        "dates": [str(d) for d in daily["timestamp"]],
        "actual": [round(v, 2) for v in daily["actual"]],
        "predicted": [round(v, 2) for v in daily["predicted"]],
    }

    # SEC by product type
    product_sec = {}
    for pt in ["L", "M", "H"]:
        subset = DF[DF["product_type"] == pt]
        product_sec[pt] = {
            "avg_sec": round(float(subset["sec_kwh_per_part"].mean()), 4),
            "count": int(len(subset)),
            "avg_deviation": round(float(subset["deviation_pct"].mean()), 1),
        }

    return templates.TemplateResponse(
        request=request,
        name="overview.html",
        context={
            "page": "overview",
            "efficiency_score": efficiency_score,
            "avg_sec": round(avg_sec, 4),
            "total_energy": round(total_energy, 0),
            "anomaly_count": anomaly_count,
            "co2_tonnes": round(co2_tonnes, 2),
            "machine_perf": machine_perf,
            "alerts": alerts[:4],
            "daily_chart": json.dumps(daily_chart),
            "product_sec": product_sec,
        },
    )


@app.get("/machine/{machine_id}", response_class=HTMLResponse)
async def machine_page(request: Request, machine_id: str):
    """Machine Deep-Dive page."""
    mdata = DF[DF["machine_id"] == machine_id]
    if mdata.empty:
        machine_id = "M-01"
        mdata = DF[DF["machine_id"] == machine_id]

    avg_sec = round(float(mdata["sec_kwh_per_part"].mean()), 4)
    avg_dev = round(float(mdata["deviation_pct"].mean()), 1)
    anom_count = int(mdata["is_anomaly"].sum())
    critical_count = int((mdata["severity"] == "critical").sum())
    maint_mode = mdata["maintenance_status"].mode().iloc[0] if len(mdata) > 0 else "Unknown"

    # Timeline data (sampled for performance)
    sample = mdata.iloc[::max(1, len(mdata) // 400)]
    timeline = {
        "timestamps": [str(t) for t in sample["timestamp"]],
        "actual": [round(v, 4) for v in sample["energy_kwh"]],
        "predicted": [round(v, 4) for v in sample["predicted_kwh"]],
        "is_anomaly": [bool(a) for a in sample["is_anomaly"]],
    }

    # Feature stats
    features_table = [
        {"name": "Torque", "value": f"{mdata['torque_nm'].mean():.1f} Nm",
         "status": "high" if mdata["torque_nm"].mean() > 45 else "normal"},
        {"name": "Process Temp", "value": f"{mdata['process_temp_k'].mean():.1f} K",
         "status": "elevated" if mdata["process_temp_k"].mean() > 311 else "normal"},
        {"name": "Tool Wear", "value": f"{mdata['tool_wear_min'].mean():.0f} min",
         "status": "moderate" if mdata["tool_wear_min"].mean() > 120 else "normal"},
        {"name": "Idle Time", "value": f"{mdata['idle_time_seconds'].mean():.0f} s",
         "status": "high" if mdata["idle_time_seconds"].mean() > 40 else "normal"},
        {"name": "Speed", "value": f"{mdata['rotational_speed_rpm'].mean():.0f} RPM",
         "status": "normal"},
    ]

    # Recent anomalies
    anomalies = mdata[mdata["is_anomaly"]].sort_values("z_score", ascending=False).head(15)
    anomaly_table = []
    for _, row in anomalies.iterrows():
        anomaly_table.append({
            "timestamp": str(row["timestamp"]),
            "actual": round(float(row["energy_kwh"]), 4),
            "predicted": round(float(row["predicted_kwh"]), 4),
            "deviation": round(float(row["deviation_pct"]), 1),
            "severity": row["severity"],
            "torque": round(float(row["torque_nm"]), 1),
            "tool_wear": int(row["tool_wear_min"]),
        })

    # Deviation histogram
    hist_values, hist_edges = np.histogram(mdata["deviation_pct"], bins=40)
    deviation_hist = {
        "bins": [round((hist_edges[i] + hist_edges[i + 1]) / 2, 1) for i in range(len(hist_values))],
        "counts": [int(v) for v in hist_values],
    }

    return templates.TemplateResponse(
        request=request,
        name="machine.html",
        context={
            "page": "machine",
            "machine_id": machine_id,
            "machines": MACHINE_IDS,
            "avg_sec": avg_sec,
            "avg_deviation": avg_dev,
            "anomaly_count": anom_count,
            "critical_count": critical_count,
            "maintenance_status": maint_mode,
            "timeline": json.dumps(timeline),
            "features_table": features_table,
            "anomaly_table": anomaly_table,
            "deviation_hist": json.dumps(deviation_hist),
        },
    )


@app.get("/whatif", response_class=HTMLResponse)
async def whatif_page(request: Request):
    """What-If Lab page."""
    baseline = {
        "torque_nm": round(float(DF["torque_nm"].median()), 1),
        "process_temp_k": round(float(DF["process_temp_k"].median()), 1),
        "rotational_speed_rpm": int(DF["rotational_speed_rpm"].median()),
        "idle_time_seconds": int(DF["idle_time_seconds"].median()),
        "tool_wear_min": int(DF["tool_wear_min"].median()),
    }
    return templates.TemplateResponse(
        request=request,
        name="whatif.html",
        context={
            "page": "whatif",
            "baseline": baseline,
        },
    )


@app.get("/recommendations", response_class=HTMLResponse)
async def recommendations_page(request: Request):
    """Recommendations page."""
    engine = RecommendationEngine(daily_production=800)
    recs = engine.generate_recommendations(DF)

    rec_list = []
    for r in recs[:8]:
        rec_list.append({
            "priority": r.priority,
            "action": r.action,
            "reason": r.reason,
            "category": r.category,
            "machine_id": r.machine_id,
            "confidence": round(r.confidence, 0),
            "difficulty": r.difficulty,
            "production_impact": r.production_impact,
            "energy_saving": round(r.expected_benefit.get("energy_saving_kwh", 0), 1),
            "cost_saving": round(r.expected_benefit.get("cost_saving_inr", 0), 0),
            "annual_saving": round(r.expected_benefit.get("annual_cost_saving_inr", 0), 0),
            "co2_reduction": round(r.expected_benefit.get("co2_reduction_kg", 0), 1),
        })

    total_annual = sum(r["annual_saving"] for r in rec_list)
    total_co2 = sum(r["co2_reduction"] for r in rec_list) * 300

    return templates.TemplateResponse(
        request=request,
        name="recommendations.html",
        context={
            "page": "recommendations",
            "recommendations": rec_list,
            "total_annual_saving": round(total_annual, 0),
            "total_annual_co2": round(total_co2, 0),
        },
    )


# ─── API Routes (JSON) ──────────────────────────────────────────────────────
@app.get("/api/simulate")
async def api_simulate(
    torque: float = 40.0,
    process_temp: float = 310.0,
    speed: int = 1500,
    idle_time: int = 30,
    tool_wear: int = 100,
    daily_production: int = 800,
):
    """What-If simulation API endpoint."""
    baseline = {
        "power_watts": float(DF["power_watts"].median()),
        "rotational_speed_rpm": float(DF["rotational_speed_rpm"].median()),
        "torque_nm": float(DF["torque_nm"].median()),
        "tool_wear_min": float(DF["tool_wear_min"].median()),
        "air_temp_k": float(DF["air_temp_k"].median()),
        "process_temp_k": float(DF["process_temp_k"].median()),
        "cycle_time_minutes": float(DF["cycle_time_minutes"].median()),
        "idle_time_seconds": float(DF["idle_time_seconds"].median()),
        "product_type_encoded": 0.0,
        "shift_encoded": 0.0,
        "maintenance_days_since": float(DF["maintenance_days_since"].median()),
        "ambient_temperature": float(DF["ambient_temperature"].median()),
    }

    modified = baseline.copy()
    modified["torque_nm"] = torque
    modified["process_temp_k"] = process_temp
    modified["rotational_speed_rpm"] = float(speed)
    modified["idle_time_seconds"] = float(idle_time)
    modified["tool_wear_min"] = float(tool_wear)
    modified["power_watts"] = torque * (speed * 2 * np.pi / 60)

    current_pred = float(MODEL.predict(pd.DataFrame([baseline]))[0])
    new_pred = float(MODEL.predict(pd.DataFrame([modified]))[0])

    delta = new_pred - current_pred
    delta_pct = (delta / current_pred * 100) if current_pred > 0 else 0

    daily_saving_kwh = -delta * daily_production
    annual_cost = daily_saving_kwh * BASE_TARIFF_INR * 300
    annual_co2 = daily_saving_kwh * GRID_EMISSION_FACTOR * 300

    return {
        "current_energy": round(current_pred, 6),
        "new_energy": round(new_pred, 6),
        "delta_kwh": round(delta, 6),
        "delta_pct": round(delta_pct, 2),
        "daily_saving_kwh": round(daily_saving_kwh, 2),
        "annual_cost_saving": round(annual_cost, 0),
        "annual_co2_reduction": round(annual_co2, 1),
        "confidence": 95 if abs(delta_pct) < 30 else 70,
        "label": "SIMULATION — Model-based estimate",
    }


@app.get("/api/health")
async def health():
    """API health check."""
    return {
        "status": "healthy",
        "model": "XGBoost",
        "dataset_rows": len(DF),
        "features": len(FEATURES),
    }
