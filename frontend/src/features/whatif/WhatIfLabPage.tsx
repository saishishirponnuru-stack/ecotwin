import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { useMutation } from '@tanstack/react-query';
import { getMachines, simulateScenario, saveScenario, listScenarios } from '../../lib/api';
import type { MachineResponse, WhatIfRequest, WhatIfResponse, ScenarioResponse } from '../../types/api';

function KpiCard({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div className="rounded border border-gray-700 bg-gray-900 p-3 text-center">
      <p className="text-xs text-gray-400 uppercase tracking-wide">{label}</p>
      <p className="mt-1 text-xl font-bold text-teal-300">{value}</p>
      {sub && <p className="text-xs text-gray-500 mt-0.5">{sub}</p>}
    </div>
  );
}

const RELIABILITY_COLOR: Record<string, string> = {
  'Interpolation (High)': 'text-green-400',
  'Mild Extrapolation (Caution)': 'text-yellow-400',
  'OOD (Unsupported)': 'text-red-400',
};

export default function WhatIfLabPage() {
  const { data: machines } = useQuery<MachineResponse[]>({
    queryKey: ['machines'],
    queryFn: getMachines,
    staleTime: 5 * 60 * 1000,
  });

  const { data: scenarios, refetch: refetchScenarios } = useQuery<ScenarioResponse[]>({
    queryKey: ['scenarios'],
    queryFn: () => listScenarios(),
    staleTime: 60 * 1000,
  });

  const [form, setForm] = React.useState<WhatIfRequest>({
    machine_id: '',
    daily_production: 800,
    tool_replacement: false,
  });
  const [scenarioName, setScenarioName] = React.useState('');
  const [result, setResult] = React.useState<WhatIfResponse | null>(null);
  const [saveMsg, setSaveMsg] = React.useState('');

  const simulateMutation = useMutation({
    mutationFn: simulateScenario,
    onSuccess: (data) => {
      setResult(data);
      setSaveMsg('');
    },
  });

  const saveMutation = useMutation({
    mutationFn: saveScenario,
    onSuccess: () => {
      setSaveMsg('Scenario saved.');
      refetchScenarios();
    },
  });

  const machineList = machines ?? [];

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.machine_id) return;
    simulateMutation.mutate(form);
  };

  const handleSave = () => {
    if (!result || !scenarioName.trim()) return;
    saveMutation.mutate({
      name: scenarioName.trim(),
      machine_id: form.machine_id,
      parameters_in: form as unknown as Record<string, unknown>,
      result_out: result as unknown as Record<string, unknown>,
    });
  };

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-semibold text-teal-300">What-If Optimization Lab</h2>
        <p className="text-sm text-gray-400 mt-0.5">
          Simulate operational parameter changes. All results are physics-based estimates — not verified measurements.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Form */}
        <div className="rounded border border-gray-700 bg-gray-800 p-4 space-y-4">
          <h3 className="text-lg font-medium text-teal-200">Scenario Parameters</h3>
          <form onSubmit={handleSubmit} className="space-y-3">
            <div>
              <label className="block text-sm text-gray-400 mb-1">Machine *</label>
              <select
                required
                className="w-full rounded border border-gray-600 bg-gray-900 px-2 py-1.5 text-sm text-gray-200"
                value={form.machine_id}
                onChange={(e) => setForm({ ...form, machine_id: e.target.value })}
              >
                <option value="">Select machine…</option>
                {machineList.map((m) => (
                  <option key={m.id} value={m.id}>
                    {m.name || m.id}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-sm text-gray-400 mb-1">Daily Production (parts)</label>
              <input
                type="number" min={1} max={5000}
                className="w-full rounded border border-gray-600 bg-gray-900 px-2 py-1.5 text-sm text-gray-200"
                value={form.daily_production ?? 800}
                onChange={(e) => setForm({ ...form, daily_production: parseInt(e.target.value) || 800 })}
              />
            </div>

            <div>
              <label className="block text-sm text-gray-400 mb-1">Spindle Speed (RPM, 500–4000)</label>
              <input
                type="number" min={500} max={4000} placeholder="Leave blank for baseline"
                className="w-full rounded border border-gray-600 bg-gray-900 px-2 py-1.5 text-sm text-gray-200"
                value={form.spindle_speed_rpm ?? ''}
                onChange={(e) => setForm({ ...form, spindle_speed_rpm: e.target.value ? parseFloat(e.target.value) : undefined })}
              />
            </div>

            <div>
              <label className="block text-sm text-gray-400 mb-1">Torque (Nm, 1–120)</label>
              <input
                type="number" min={1} max={120} placeholder="Leave blank for baseline"
                className="w-full rounded border border-gray-600 bg-gray-900 px-2 py-1.5 text-sm text-gray-200"
                value={form.torque_nm ?? ''}
                onChange={(e) => setForm({ ...form, torque_nm: e.target.value ? parseFloat(e.target.value) : undefined })}
              />
            </div>

            <div>
              <label className="block text-sm text-gray-400 mb-1">Idle Cutoff (seconds, 0–120)</label>
              <input
                type="number" min={0} max={120} placeholder="Leave blank for baseline"
                className="w-full rounded border border-gray-600 bg-gray-900 px-2 py-1.5 text-sm text-gray-200"
                value={form.idle_cutoff_seconds ?? ''}
                onChange={(e) => setForm({ ...form, idle_cutoff_seconds: e.target.value ? parseFloat(e.target.value) : undefined })}
              />
            </div>

            <div>
              <label className="block text-sm text-gray-400 mb-1">Shift Reschedule</label>
              <select
                className="w-full rounded border border-gray-600 bg-gray-900 px-2 py-1.5 text-sm text-gray-200"
                value={form.shift_reschedule ?? ''}
                onChange={(e) => setForm({ ...form, shift_reschedule: e.target.value || null })}
              >
                <option value="">No change</option>
                <option value="Day">Day</option>
                <option value="Evening">Evening</option>
                <option value="Night">Night</option>
              </select>
            </div>

            <div className="flex items-center gap-2">
              <input
                type="checkbox" id="tool_replacement"
                checked={form.tool_replacement ?? false}
                onChange={(e) => setForm({ ...form, tool_replacement: e.target.checked })}
              />
              <label htmlFor="tool_replacement" className="text-sm text-gray-400">Simulate tool replacement</label>
            </div>

            <button
              type="submit"
              disabled={simulateMutation.isPending || !form.machine_id}
              className="w-full rounded bg-teal-600 py-2 text-sm font-medium text-white hover:bg-teal-500 disabled:opacity-50"
            >
              {simulateMutation.isPending ? 'Simulating…' : 'Run Simulation'}
            </button>

            {simulateMutation.isError && (
              <p className="text-sm text-red-400">
                {(simulateMutation.error as Error).message}
              </p>
            )}
          </form>
        </div>

        {/* Results */}
        <div className="rounded border border-gray-700 bg-gray-800 p-4 space-y-4">
          <h3 className="text-lg font-medium text-teal-200">Simulation Results</h3>
          {!result && !simulateMutation.isPending && (
            <p className="text-gray-500 text-sm">Run a simulation to see results here.</p>
          )}
          {simulateMutation.isPending && (
            <div className="flex items-center gap-2 text-gray-300">
              <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-teal-400" />
              <span>Computing…</span>
            </div>
          )}
          {result && (
            <div className="space-y-4">
              <div className="rounded bg-gray-900 p-2 text-center">
                <span className={`text-xs font-medium ${RELIABILITY_COLOR[result.reliability_status] ?? 'text-gray-400'}`}>
                  {result.reliability_status}
                </span>
                <p className="text-xs text-gray-500 mt-0.5">{result.label}</p>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <KpiCard label="Baseline Energy" value={`${result.baseline_energy_kwh.toFixed(2)} kWh`} sub="Current operation" />
                <KpiCard label="Simulated Energy" value={`${result.simulated_energy_kwh.toFixed(2)} kWh`} sub="With changes" />
                <KpiCard
                  label="Energy Delta"
                  value={`${result.delta_pct >= 0 ? '+' : ''}${result.delta_pct.toFixed(1)}%`}
                  sub={`${result.delta_energy_kwh.toFixed(2)} kWh`}
                />
                <KpiCard label="Daily Saving" value={`${result.daily_saving_kwh.toFixed(2)} kWh`} />
                <KpiCard label="Annual Cost Saving" value={`₹${result.annual_cost_saving_inr.toLocaleString()}`} sub="Estimate" />
                <KpiCard label="Annual CO₂ Reduction" value={`${result.annual_co2_reduction_kg.toFixed(1)} kg`} sub="Estimate" />
              </div>

              {result.warnings.length > 0 && (
                <div className="rounded border border-yellow-700 bg-yellow-900/20 p-3 space-y-1">
                  {result.warnings.map((w, i) => (
                    <p key={i} className="text-xs text-yellow-300">⚠ {w}</p>
                  ))}
                </div>
              )}

              {/* Save scenario */}
              <div className="flex gap-2">
                <input
                  type="text"
                  placeholder="Scenario name…"
                  className="flex-1 rounded border border-gray-600 bg-gray-900 px-2 py-1 text-sm text-gray-200"
                  value={scenarioName}
                  onChange={(e) => setScenarioName(e.target.value)}
                />
                <button
                  onClick={handleSave}
                  disabled={saveMutation.isPending || !scenarioName.trim()}
                  className="rounded bg-teal-700 px-3 py-1 text-sm hover:bg-teal-600 disabled:opacity-50"
                >
                  Save
                </button>
              </div>
              {saveMsg && <p className="text-xs text-green-400">{saveMsg}</p>}
            </div>
          )}
        </div>
      </div>

      {/* Saved scenarios */}
      {scenarios && scenarios.length > 0 && (
        <div className="rounded border border-gray-700 bg-gray-800 p-4">
          <h3 className="text-lg font-medium text-teal-200 mb-3">Saved Scenarios ({scenarios.length})</h3>
          <div className="overflow-x-auto">
            <table className="w-full text-sm text-gray-200">
              <thead className="border-b border-gray-700">
                <tr>
                  <th className="px-2 py-1 text-left text-gray-400">Name</th>
                  <th className="px-2 py-1 text-left text-gray-400">Machine</th>
                  <th className="px-2 py-1 text-right text-gray-400">Delta %</th>
                  <th className="px-2 py-1 text-right text-gray-400">Annual Saving ₹</th>
                  <th className="px-2 py-1 text-left text-gray-400">Saved</th>
                </tr>
              </thead>
              <tbody>
                {scenarios.map((s) => (
                  <tr key={s.id} className="border-b border-gray-700 hover:bg-gray-700">
                    <td className="px-2 py-1">{s.name}</td>
                    <td className="px-2 py-1">{s.machine_id}</td>
                    <td className="px-2 py-1 text-right">
                      {typeof s.result_out['delta_pct'] === 'number' ? `${(s.result_out['delta_pct'] as number).toFixed(1)}%` : '—'}
                    </td>
                    <td className="px-2 py-1 text-right">
                      {typeof s.result_out['annual_cost_saving_inr'] === 'number'
                        ? `₹${(s.result_out['annual_cost_saving_inr'] as number).toLocaleString()}`
                        : '—'}
                    </td>
                    <td className="px-2 py-1 text-gray-400">{new Date(s.created_at).toLocaleDateString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
