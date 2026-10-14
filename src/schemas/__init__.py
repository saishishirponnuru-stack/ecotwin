"""
Pydantic v2 schemas for EcoTwin API.
"""

from typing import List, Dict, Any, Optional, Literal
from math import isfinite
from datetime import datetime
from pydantic import BaseModel, Field, field_validator


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
    cost_inr: Optional[float] = None
    co2_tonnes: Optional[float] = None
    fleet_summary: List[MachineOverviewItem]
    daily_trend: List[DailyTrendItem]
    est_wasted_cost_inr: Optional[float] = None
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


class DemoDataResetRequest(BaseModel):
    confirm: Literal[True] = Field(..., description="Explicit user confirmation is required")


class DemoDataResetResponse(BaseModel):
    status: Literal["success"] = "success"
    updated_count: int
    total_demo_anomalies: int
    open_demo_anomalies: int
    resolved_demo_anomalies: int
    backup_file: Optional[str] = None
    message: str


# ─── What-If Simulation ──────────────────────────────────────────────────────
class WhatIfRequest(BaseModel):
    machine_id: str = Field(..., description="Target machine (e.g. 'M-02')")
    spindle_speed_rpm: Optional[float] = Field(None, ge=500, le=4000, description="Modified spindle RPM")
    torque_nm: Optional[float] = Field(None, ge=1, le=120, description="Modified spindle torque")
    tool_replacement: Optional[bool] = Field(False, description="Simulate replacing worn cutting tool")
    idle_cutoff_seconds: Optional[float] = Field(None, ge=0, le=120, description="Optimized idle standby delay")
    shift_reschedule: Optional[Literal["Day", "Evening", "Night"]] = Field(None, description="Reschedule batch to Day, Evening, or Night")
    daily_production: Optional[int] = Field(800, ge=1, le=5000, description="Parts per day")

    @field_validator("spindle_speed_rpm", "torque_nm", "idle_cutoff_seconds")
    @classmethod
    def finite_operating_value(cls, value: Optional[float]) -> Optional[float]:
        if value is not None and not isfinite(value):
            raise ValueError("Operating values must be finite")
        return value


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

# ─── Recommendations ────────────────────────────────────────────────────────
class RecommendationItem(BaseModel):
    id: int = Field(..., description="Unique recommendation identifier")
    machine_id: Optional[str] = Field(None, description="Target machine, if applicable")
    category: str = Field(..., description="High‑level category (e.g., Efficiency, Maintenance)")
    action: str = Field(..., description="Suggested concrete action for the operator")
    reason: str = Field(..., description="Why this recommendation is made, referencing data sources")
    expected_benefit: Dict[str, Any] = Field(..., description="Estimated impact, e.g., {'energy_kwh': 10.5, 'cost_inr': 250}")
    difficulty: str = Field(..., description="Operational difficulty (Low/Medium/High)")
    evidence_source: str = Field(..., description="Origin of evidence, e.g., telemetry, anomaly")
    evidence_summary: str = Field(..., description="Observed rule trigger and sample size; not a predictive confidence score")
    provenance: str = Field(..., description="Data provenance tier for this recommendation")
    assumptions: Optional[str] = Field(None, description="Assumptions underpinning the estimate")

class RecommendationListResponse(BaseModel):
    recommendations: List[RecommendationItem]
