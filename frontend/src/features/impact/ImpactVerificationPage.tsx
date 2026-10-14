import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { getMachines, listScenarios, getAnomalies } from '../../lib/api';
import type { MachineResponse, ScenarioResponse } from '../../types/api';

/**
 * Impact Verification page.
 *
 * This page compares "before" (baseline from saved What-If scenarios) with
 * "after" (anomalies that appeared after an intervention date).
 *
 * Since EcoTwin does not yet have a dedicated impact tracking database,
 * this page:
 * 1. Shows saved What-If scenarios as the simulated / expected impact.
 * 2. Shows current anomaly counts as the observed state.
 * 3. Clearly labels all figures as SIMULATED or OBSERVED — never "verified savings".
 */

function SectionLabel({ type }: { type: 'SIMULATED' | 'OBSERVED' | 'VERIFIED' }) {
  const colors = {
    SIMULATED: 'bg-blue-800 text-blue-200',
    OBSERVED: 'bg-teal-800 text-teal-200',
    VERIFIED: 'bg-green-800 text-green-200',
  };
  return (
    <span className={`rounded px-2 py-0.5 text-xs font-medium ${colors[type]}`}>{type}</span>
  );
}

function formatMetric(value: unknown, digits = 2) {
  return typeof value === 'number' && Number.isFinite(value) ? value.toFixed(digits) : 'Unavailable';
}

function formatCurrency(value: unknown) {
  return typeof value === 'number' && Number.isFinite(value) ? `₹${value.toLocaleString()}` : 'Unavailable';
}

export default function ImpactVerificationPage() {
  const [machineId, setMachineId] = React.useState('');
  const [scenarioId, setScenarioId] = React.useState<number | null>(null);

  const { data: machines } = useQuery<MachineResponse[]>({
    queryKey: ['machines'],
    queryFn: getMachines,
    staleTime: 5 * 60 * 1000,
  });

  const { data: scenarios } = useQuery<ScenarioResponse[]>({
    queryKey: ['scenarios', machineId],
    queryFn: () => listScenarios(machineId || undefined),
    staleTime: 60 * 1000,
  });

  const {
    data: anomalies,
    isLoading: anomaliesLoading,
    isError: anomaliesError,
    refetch: refetchAnomalies,
  } = useQuery({
    queryKey: ['anomalies', machineId, ''],
    queryFn: () => getAnomalies({ machine_id: machineId || undefined, limit: 500 }),
    staleTime: 2 * 60 * 1000,
  });

  const machineList = machines ?? [];
  const scenarioList = scenarios ?? [];

  const applicableScenarios = machineId
    ? scenarioList.filter((scenario) => scenario.machine_id === machineId)
    : scenarioList;
  const selectedScenario = applicableScenarios.find((scenario) => scenario.id === scenarioId)
    ?? applicableScenarios[0];

  const resolvedAnomalies = anomalies?.anomalies.filter((anomaly) => anomaly.is_resolved);
  const resolvedPotentialSavings = resolvedAnomalies?.map((anomaly) => anomaly.potential_saving_kwh);
  const resolvedCount = resolvedAnomalies?.length;
  const openCount = anomalies?.anomalies.filter((anomaly) => !anomaly.is_resolved).length;
  const potentialSavedKwh = resolvedPotentialSavings?.every(Number.isFinite)
    ? resolvedPotentialSavings.reduce((sum, value) => sum + value, 0)
    : undefined;
  const anomalyUnavailable = anomaliesLoading ? 'Loading…' : 'Unavailable';

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-semibold text-teal-300">Impact Verification</h2>
        <p className="text-sm text-gray-400 mt-0.5">
          Compare simulated projections from What-If scenarios with observed anomaly resolution data.
          <span className="ml-2 text-yellow-400">Figures are not verified measurements unless specifically labelled.</span>
        </p>
      </div>

      {/* Machine selector */}
      <div className="flex gap-3 items-center">
        <label className="text-sm text-gray-400">Filter by machine:</label>
        <select
          className="rounded border border-gray-600 bg-gray-800 px-2 py-1 text-sm text-gray-200"
          value={machineId}
          onChange={(e) => setMachineId(e.target.value)}
        >
          <option value="">All Machines</option>
          {machineList.map((m) => {
            return <option key={m.id} value={m.id}>{m.name || m.id}</option>;
          })}
        </select>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* Simulated impact */}
        <div className="rounded border border-blue-800 bg-gray-800 p-4 space-y-3">
          <div className="flex items-center gap-2">
            <h3 className="text-lg font-medium text-blue-300">Projected Impact</h3>
            <SectionLabel type="SIMULATED" />
          </div>
          <p className="text-xs text-gray-400">
            Select one saved scenario. Alternatives are intentionally not summed because they may describe
            mutually exclusive changes to the same machine and production period.
          </p>
          {applicableScenarios.length === 0 ? (
            <p className="text-sm text-gray-500">No saved scenarios found. Use the What-If Lab to create and save scenarios.</p>
          ) : (
            <>
              <select
                className="w-full rounded border border-gray-600 bg-gray-900 px-2 py-1.5 text-sm text-gray-200"
                value={selectedScenario?.id ?? ''}
                onChange={(event) => setScenarioId(Number(event.target.value))}
              >
                {applicableScenarios.map((scenario) => (
                  <option key={scenario.id} value={scenario.id}>{scenario.name} — {scenario.machine_id}</option>
                ))}
              </select>
              <div className="grid grid-cols-3 gap-3">
              {[
                { label: 'Daily Energy Saving', value: `${formatMetric(selectedScenario?.result_out['daily_saving_kwh'])} kWh`, sub: 'SIMULATED' },
                { label: 'Ann. Cost Saving (Est.)', value: formatCurrency(selectedScenario?.result_out['annual_cost_saving_inr']), sub: 'SIMULATED' },
                { label: 'Ann. CO₂ Reduction (Est.)', value: `${formatMetric(selectedScenario?.result_out['annual_co2_reduction_kg'], 1)} kg`, sub: 'SIMULATED' },
              ].map((kpi) => (
                <div key={kpi.label} className="rounded bg-gray-900 p-2 text-center">
                  <p className="text-xs text-gray-400">{kpi.label}</p>
                  <p className="text-base font-bold text-blue-300 mt-1">{kpi.value}</p>
                  <p className="text-xs text-gray-500">{kpi.sub}</p>
                </div>
              ))}
              </div>
            </>
          )}
          {applicableScenarios.length > 0 && (
            <div className="overflow-x-auto mt-2">
              <table className="w-full text-xs text-gray-300">
                <thead className="border-b border-gray-700">
                  <tr>
                    <th className="px-2 py-1 text-left text-gray-400">Scenario</th>
                    <th className="px-2 py-1 text-left text-gray-400">Machine</th>
                    <th className="px-2 py-1 text-right text-gray-400">Daily kWh</th>
                    <th className="px-2 py-1 text-right text-gray-400">Reliability</th>
                  </tr>
                </thead>
                <tbody>
                  {applicableScenarios.map((s) => (
                    <tr key={s.id} className="border-b border-gray-700">
                      <td className="px-2 py-1">{s.name}</td>
                      <td className="px-2 py-1">{s.machine_id}</td>
                      <td className="px-2 py-1 text-right">{formatMetric(s.result_out['daily_saving_kwh'])}</td>
                      <td className="px-2 py-1 text-right text-xs text-gray-500">
                        {String(s.result_out['reliability_status'] ?? '—').split(' ')[0]}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* Observed impact */}
        <div className="rounded border border-teal-800 bg-gray-800 p-4 space-y-3">
          <div className="flex items-center gap-2">
            <h3 className="text-lg font-medium text-teal-300">Observed State</h3>
            <SectionLabel type="OBSERVED" />
          </div>
          <p className="text-xs text-gray-400">
            Derived from anomaly resolution records in the telemetry database.
          </p>
          {anomaliesError && (
            <div role="alert" className="rounded border border-red-700 bg-red-900/30 p-2 text-sm text-red-300">
              Failed to load anomaly records.
              <button className="ml-2 rounded bg-teal-600 px-2 py-0.5 text-xs text-white hover:bg-teal-500" onClick={() => refetchAnomalies()}>Retry</button>
            </div>
          )}
          <div className="grid grid-cols-3 gap-3">
            {[
              { label: 'Open Anomalies', value: openCount ?? anomalyUnavailable, color: 'text-red-300' },
              { label: 'Resolved Anomalies', value: resolvedCount ?? anomalyUnavailable, color: 'text-teal-300' },
              { label: 'Excess Energy in Resolved Events', value: potentialSavedKwh == null ? anomalyUnavailable : `${potentialSavedKwh.toFixed(2)} kWh`, color: 'text-yellow-300' },
            ].map((kpi) => (
              <div key={kpi.label} className="rounded bg-gray-900 p-2 text-center">
                <p className="text-xs text-gray-400">{kpi.label}</p>
                <p className={`text-base font-bold mt-1 ${kpi.color}`}>{kpi.value}</p>
              </div>
            ))}
          </div>

          <div className="rounded border border-gray-700 bg-gray-900/50 p-3 text-xs text-gray-400 space-y-1">
            <p className="font-medium text-yellow-400">Verification Gap</p>
            <p>
              EcoTwin does not yet have pre/post intervention measurement periods stored. Resolving an anomaly
              records an operator action; it does not prove energy was saved.
              True M&amp;V (Measurement and Verification) requires:
            </p>
            <ul className="list-disc list-inside space-y-0.5 mt-1">
              <li>A defined baseline measurement period.</li>
              <li>A post-intervention measurement period.</li>
              <li>Normalized comparison accounting for production volume and ambient conditions.</li>
            </ul>
            <p className="mt-2 text-gray-500">
              Use the Anomaly Center to resolve anomalies, then compare anomaly counts over time as a leading indicator.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
