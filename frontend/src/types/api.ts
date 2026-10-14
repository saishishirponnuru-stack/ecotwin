// Types for EcoTwin API responses

// ── Overview ──────────────────────────────────────────────────────────────────
export interface OverviewResponse {
  facility_health_score: number;
  avg_sec_kwh_per_part: number;
  total_energy_kwh: number;
  total_anomalies: number;
  est_co2_tonnes: number;
  cost_inr?: number;
  co2_tonnes?: number;
  est_wasted_cost_inr?: number;
  grid_emission_factor_kg_per_kwh?: number;
  total_parts_produced?: number;
  facility_name?: string;
  reporting_window?: string;
  fleet_summary: Array<{
    id: string;
    name: string;
    status: string;
    efficiency_score: number;
    avg_sec: number;
    total_anomalies: number;
    avg_deviation_pct: number;
    provenance_tier: string;
  }>;
  daily_trend: Array<{
    date: string;
    actual_kwh: number;
    baseline_kwh: number;
    savings_opportunity_kwh: number;
  }>;
}

// ── Machines ──────────────────────────────────────────────────────────────────
export interface MachineResponse {
  id: string;
  name: string;
  model_type: string;
  rated_power_kw: number;
  status: string;
  latest_reading?: Record<string, unknown> | null;
}

export interface MachineComparisonResponse {
  machine_id: string;
  machine_name: string;
  avg_sec_kwh_per_part: number | null;
  total_energy_kwh: number | null;
  cost_inr: number | null;
  co2_tonnes: number | null;
}

export interface MachineDetailResponse {
  machine: {
    id: string;
    name: string;
    model_type: string;
    rated_power_kw: number;
    status: string;
    latest_reading?: Record<string, unknown>;
  };
  operating_stats: Record<string, unknown>;
  recent_readings: Array<Record<string, unknown>>;
  active_anomalies: Array<Record<string, unknown>>;
}

// ── Telemetry ─────────────────────────────────────────────────────────────────
export interface TelemetryResponse {
  machine_id: string;
  timestamps: string[];
  actual: number[];
  predicted: number[];
  is_anomaly: boolean[];
}

// ── Anomalies ─────────────────────────────────────────────────────────────────
export interface AnomalyItem {
  id: number;
  telemetry_id?: number;
  machine_id: string;
  timestamp: string;
  actual_kwh: number;
  predicted_kwh: number;
  residual_kwh: number;
  z_score: number;
  severity: string;
  reason_code: string;
  contributors?: Record<string, unknown>;
  potential_saving_kwh: number;
  is_resolved: boolean;
}

export interface AnomalyListResponse {
  total_count: number;
  critical_count: number;
  warning_count: number;
  watch_count: number;
  anomalies: AnomalyItem[];
}

// ── Recommendations ───────────────────────────────────────────────────────────
export interface RecommendationItem {
  id: number;
  machine_id?: string;
  category: string;
  action: string;
  reason: string;
  expected_benefit: {
    energy_kwh?: number;
    cost_inr?: number;
    co2_tonnes?: number;
    [key: string]: unknown;
  };
  difficulty: string;
  evidence_source: string;
  evidence_summary: string;
  provenance: string;
  assumptions?: string;
}

export interface RecommendationListResponse {
  recommendations: RecommendationItem[];
}

// ── What-If Lab ───────────────────────────────────────────────────────────────
export interface WhatIfRequest {
  machine_id: string;
  spindle_speed_rpm?: number | null;
  torque_nm?: number | null;
  tool_replacement?: boolean;
  idle_cutoff_seconds?: number | null;
  shift_reschedule?: string | null;
  daily_production?: number;
}

export interface WhatIfResponse {
  baseline_energy_kwh: number;
  simulated_energy_kwh: number;
  delta_energy_kwh: number;
  delta_pct: number;
  daily_saving_kwh: number;
  annual_cost_saving_inr: number;
  annual_co2_reduction_kg: number;
  ood_distance: number;
  reliability_status: string;
  warnings: string[];
  physical_tradeoffs: Record<string, unknown>;
  label: string;
}

export interface ScenarioResponse {
  id: number;
  name: string;
  machine_id: string;
  parameters_in: Record<string, unknown>;
  result_out: Record<string, unknown>;
  created_at: string;
}

// ── Config / Settings ─────────────────────────────────────────────────────────
export interface ConfigItem {
  key: string;
  value: string;
  description?: string;
  updated_at?: string;
}

export interface DemoDataResetResponse {
  status: 'success';
  updated_count: number;
  total_demo_anomalies: number;
  open_demo_anomalies: number;
  resolved_demo_anomalies: number;
  backup_file?: string | null;
  message: string;
}
