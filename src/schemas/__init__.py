"""
Pydantic v2 schemas for EcoTwin API.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field


# ─── Health ──────────────────────────────────────────────────────────────────
class HealthResponse(BaseModel):
    status: str = Field(..., description="API operational status")
    database: str = Field(..., description="Database engine type (SQLite / PostgreSQL)")
    total_telemetry_records: int
    total_machines: int
    data_provenance_model: str = "5-Tier Categorized"


# ─── Executive Overview ──────────────────────────────────────────────────────
class MachineOverviewItem(BaseModel):
    id: str
    name: str
    status: str
    efficiency_score: float
    avg_sec: float
    total_anomalies: int
    avg_deviation_pct: float
    provenance_tier: str


class DailyTrendItem(BaseModel):
    date: str
    actual_kwh: float
    baseline_kwh: float
    savings_opportunity_kwh: float


class ExecutiveOverviewResponse(BaseModel):
    facility_name: str
    reporting_window: str
    total_energy_kwh: float
    avg_sec_kwh_per_part: float
    total_parts_produced: int
    total_anomalies: int
    facility_health_score: float
    est_co2_tonnes: float
    est_wasted_cost_inr: float
    fleet_summary: List[MachineOverviewItem]
    daily_trend: List[DailyTrendItem]
    tariff_inr_per_kwh: float
    grid_emission_factor_kg_per_kwh: float
    data_provenance: str = "TIER_2_PHYSICALLY_DERIVED with TIER_3_CALIBRATED_CONTEXT"


# ─── Machines ────────────────────────────────────────────────────────────────
class MachineListItem(BaseModel):
    id: str
    name: str
    model_type: str
    rated_power_kw: float
    status: str
    latest_reading: Optional[Dict[str, Any]] = None


class MachineDetailResponse(BaseModel):
    machine: MachineListItem
    operating_stats: Dict[str, Any]
    recent_readings: List[Dict[str, Any]]
    active_anomalies: List[Dict[str, Any]]


# ─── Telemetry ───────────────────────────────────────────────────────────────
class TelemetryListResponse(BaseModel):
    total_count: int
    page: int
    limit: int
    records: List[Dict[str, Any]]


# ─── Anomalies ───────────────────────────────────────────────────────────────
class AnomalyItem(BaseModel):
    id: int
    telemetry_id: Optional[int]
    machine_id: str
    timestamp: str
    actual_kwh: float
    predicted_kwh: float
    residual_kwh: float
    z_score: float
    severity: str
    reason_code: str
    contributors: Optional[Dict[str, Any]]
    potential_saving_kwh: float
    is_resolved: bool


class AnomalyListResponse(BaseModel):
    total_count: int
    critical_count: int
    warning_count: int
    watch_count: int
    anomalies: List[AnomalyItem]


class AnomalyResolveRequest(BaseModel):
    resolution_notes: Optional[str] = "Resolved by operator"


# ─── What-If Simulation ──────────────────────────────────────────────────────
class WhatIfRequest(BaseModel):
    machine_id: str = Field(..., description="Target machine (e.g. 'M-02')")
    spindle_speed_rpm: Optional[float] = Field(None, ge=500, le=4000, description="Modified spindle RPM")
    torque_nm: Optional[float] = Field(None, ge=1, le=120, description="Modified spindle torque")
    tool_replacement: Optional[bool] = Field(False, description="Simulate replacing worn cutting tool")
    idle_cutoff_seconds: Optional[float] = Field(None, ge=0, le=120, description="Optimized idle standby delay")
    shift_reschedule: Optional[str] = Field(None, description="Reschedule batch to 'Day', 'Evening', or 'Night'")
    daily_production: Optional[int] = Field(800, ge=1, le=5000, description="Parts per day")


class WhatIfResponse(BaseModel):
    baseline_energy_kwh: float
    simulated_energy_kwh: float
    delta_energy_kwh: float
    delta_pct: float
    daily_saving_kwh: float
    annual_cost_saving_inr: float
    annual_co2_reduction_kg: float
    ood_distance: float
    reliability_status: str  # 'Interpolation (High)', 'Mild Extrapolation (Caution)', 'OOD (Unsupported)'
    warnings: List[str]
    physical_tradeoffs: Dict[str, Any]
    label: str = "SIMULATION — Physics & Empirical Estimate"


class ScenarioSaveRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    machine_id: str
    parameters_in: Dict[str, Any]
    result_out: Dict[str, Any]


class ScenarioResponse(BaseModel):
    id: int
    name: str
    machine_id: str
    parameters_in: Dict[str, Any]
    result_out: Dict[str, Any]
    created_at: str


# ─── Config ──────────────────────────────────────────────────────────────────
class ConfigItem(BaseModel):
    key: str
    value: str
    description: Optional[str] = None
    updated_at: Optional[str] = None


class ConfigUpdateRequest(BaseModel):
    settings: Dict[str, str] = Field(..., description="Dictionary of key-value settings to update")
