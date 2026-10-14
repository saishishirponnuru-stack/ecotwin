import {
  OverviewResponse,
  MachineResponse,
  TelemetryResponse,
  MachineDetailResponse,
  RecommendationListResponse,
  AnomalyListResponse,
  WhatIfRequest,
  WhatIfResponse,
  ScenarioResponse,
  ConfigItem,
  MachineComparisonResponse,
  DemoDataResetResponse,
} from '../types/api';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api';

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const resp = await fetch(`${API_BASE_URL}${path}`, options);
  if (!resp.ok) {
    const txt = await resp.text();
    throw new Error(`API error ${resp.status}: ${txt}`);
  }
  return resp.json() as Promise<T>;
}

async function postJson<T>(path: string, body: unknown): Promise<T> {
  return request<T>(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
}

async function putJson<T>(path: string, body: unknown): Promise<T> {
  return request<T>(path, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
}

// ── Overview ──────────────────────────────────────────────────────────────────
export const getOverview = () => request<OverviewResponse>('/v1/overview');

// ── Machines ──────────────────────────────────────────────────────────────────
export const getMachines = () => request<MachineResponse[]>('/v1/machines');
export const getMachineDetail = (machineId: string) =>
  request<MachineDetailResponse>(`/v1/machines/${encodeURIComponent(machineId)}`);

// ── Telemetry ─────────────────────────────────────────────────────────────────
export const getTelemetry = (machineId: string) =>
  request<TelemetryResponse>(`/v1/telemetry?machine_id=${encodeURIComponent(machineId)}`);

// ── Recommendations ───────────────────────────────────────────────────────────
export const getRecommendations = () =>
  request<RecommendationListResponse>('/v1/recommendations');

// ── Anomalies ─────────────────────────────────────────────────────────────────
export const getAnomalies = (params?: { machine_id?: string; severity?: string; is_resolved?: boolean; limit?: number; offset?: number }) => {
  const qs = new URLSearchParams();
  if (params?.machine_id) qs.set('machine_id', params.machine_id);
  if (params?.severity) qs.set('severity', params.severity);
  if (params?.is_resolved !== undefined) qs.set('is_resolved', String(params.is_resolved));
  if (params?.limit !== undefined) qs.set('limit', String(params.limit));
  if (params?.offset !== undefined) qs.set('offset', String(params.offset));
  const q = qs.toString() ? `?${qs.toString()}` : '';
  return request<AnomalyListResponse>(`/v1/anomalies${q}`);
};

export const resolveAnomaly = (anomalyId: number, notes: string) =>
  postJson<unknown>(`/v1/anomalies/${anomalyId}/resolve`, { resolution_notes: notes });

// ── What-If Lab ───────────────────────────────────────────────────────────────
export const simulateScenario = (payload: WhatIfRequest) =>
  postJson<WhatIfResponse>('/v1/whatif/simulate', payload);

export const saveScenario = (payload: {
  name: string;
  machine_id: string;
  parameters_in: Record<string, unknown>;
  result_out: Record<string, unknown>;
}) => postJson<ScenarioResponse>('/v1/whatif/save', payload);

export const listScenarios = (machineId?: string) => {
  const qs = machineId ? `?machine_id=${encodeURIComponent(machineId)}` : '';
  return request<ScenarioResponse[]>(`/v1/whatif/scenarios${qs}`);
};

// ── Energy ────────────────────────────────────────────────────────────────────
export const getEnergyOverview = () =>
  request<OverviewResponse>('/v1/energy/overview');

export const getEnergyMachineComparison = () =>
  request<MachineComparisonResponse[]>('/v1/energy/machine-comparison');

// ── Config / Settings ─────────────────────────────────────────────────────────
export const getConfig = () => request<ConfigItem[]>('/v1/config');

export const updateConfig = (settings: Record<string, string>) =>
  putJson<ConfigItem[]>('/v1/config', { settings });

// ── Demo Data ─────────────────────────────────────────────────────────────────
export const resetDemoData = () =>
  postJson<DemoDataResetResponse>('/v1/demo-data/reset', { confirm: true });
