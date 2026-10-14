import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { getEnergyOverview, getEnergyMachineComparison } from '../../lib/api';
import type { MachineComparisonResponse } from '../../types/api';

function KpiCard({ label, value, unit, sub }: { label: string; value: string | number; unit?: string; sub?: string }) {
  return (
    <div className="rounded border border-gray-700 bg-gray-900 p-4">
      <p className="text-xs text-gray-400 uppercase tracking-wide">{label}</p>
      <p className="mt-1 text-2xl font-bold text-teal-300">
        {typeof value === 'number' ? value.toLocaleString(undefined, { maximumFractionDigits: 2 }) : value}
        {unit && <span className="text-sm text-gray-400 ml-1">{unit}</span>}
      </p>
      {sub && <p className="text-xs text-gray-500 mt-0.5">{sub}</p>}
    </div>
  );
}

function formatMetric(value: number | null | undefined, digits: number) {
  return typeof value === 'number' && Number.isFinite(value)
    ? value.toLocaleString(undefined, { minimumFractionDigits: digits, maximumFractionDigits: digits })
    : 'Unavailable';
}

export default function EnergyIntelligencePage() {
  const { data: overview, error: overviewError, isLoading: overviewLoading, refetch } = useQuery({
    queryKey: ['energyOverview'],
    queryFn: getEnergyOverview,
    staleTime: 5 * 60 * 1000,
  });

  const { data: comparison, isLoading: compLoading } = useQuery({
    queryKey: ['energyComparison'],
    queryFn: getEnergyMachineComparison,
    staleTime: 5 * 60 * 1000,
  });

  const compData: MachineComparisonResponse[] = comparison ?? [];

  const isLoading = overviewLoading || compLoading;

  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center py-16 text-gray-300">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-teal-400" />
        <p className="mt-3 text-sm">Loading energy data…</p>
      </div>
    );
  }

  if (overviewError) {
    return (
      <div className="rounded border border-red-700 bg-red-900/30 p-4 text-red-300">
        Failed to load energy overview.
        <button className="ml-3 rounded bg-teal-600 px-2 py-0.5 text-sm hover:bg-teal-500" onClick={() => refetch()}>Retry</button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-semibold text-teal-300">Energy Intelligence</h2>
          {overview?.reporting_window && (
            <p className="text-sm text-gray-400 mt-0.5">Reporting window: {overview.reporting_window}</p>
          )}
        </div>
        <button
          className="rounded border border-gray-600 bg-gray-700 px-3 py-1 text-sm text-gray-200 hover:bg-gray-600"
          onClick={() => refetch()}
        >
          Refresh
        </button>
      </div>

      {/* KPI grid */}
      {overview && (
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
          <KpiCard label="Total Energy" value={formatMetric(overview.total_energy_kwh, 1)} unit="kWh" />
          <KpiCard label="Avg SEC" value={formatMetric(overview.avg_sec_kwh_per_part, 4)} unit="kWh/part" />
          <KpiCard
            label="Est. Cost"
            value={overview.cost_inr == null || !Number.isFinite(overview.cost_inr) ? 'Unavailable' : `₹${formatMetric(overview.cost_inr, 0)}`}
            sub="Based on configured tariff"
          />
          <KpiCard
            label="Est. CO₂"
            value={formatMetric(overview.est_co2_tonnes, 3)}
            unit="tonnes"
            sub={`Grid: ${formatMetric(overview.grid_emission_factor_kg_per_kwh, 3)} kg/kWh`}
          />
          <KpiCard label="Facility Health" value={`${formatMetric(overview.facility_health_score, 1)}%`} />
          <KpiCard label="Anomalies" value={formatMetric(overview.total_anomalies, 0)} />
          {overview.est_wasted_cost_inr !== undefined && (
            <KpiCard label="Wasted Cost (Est.)" value={overview.est_wasted_cost_inr == null || !Number.isFinite(overview.est_wasted_cost_inr) ? 'Unavailable' : `₹${formatMetric(overview.est_wasted_cost_inr, 0)}`} sub="From anomalous energy" />
          )}
          {overview.total_parts_produced !== undefined && (
            <KpiCard label="Parts Produced" value={formatMetric(overview.total_parts_produced, 0)} />
          )}
        </div>
      )}

      {/* Daily trend */}
      {overview && overview.daily_trend && overview.daily_trend.length > 0 && (
        <div className="rounded border border-gray-700 bg-gray-800 p-4">
          <h3 className="text-lg font-medium text-teal-200 mb-3">Daily Energy Trend</h3>
          <div className="overflow-x-auto">
            <table className="w-full text-sm text-gray-200">
              <thead className="border-b border-gray-700">
                <tr>
                  <th className="px-2 py-1 text-left text-gray-400">Date</th>
                  <th className="px-2 py-1 text-right text-gray-400">Actual (kWh)</th>
                  <th className="px-2 py-1 text-right text-gray-400">Baseline (kWh)</th>
                  <th className="px-2 py-1 text-right text-gray-400">Savings Opportunity (kWh)</th>
                </tr>
              </thead>
              <tbody>
                {overview.daily_trend.map((d) => (
                  <tr key={d.date} className="border-b border-gray-700 hover:bg-gray-700">
                    <td className="px-2 py-1">{d.date}</td>
                    <td className="px-2 py-1 text-right">{formatMetric(d.actual_kwh, 2)}</td>
                    <td className="px-2 py-1 text-right text-teal-300">{formatMetric(d.baseline_kwh, 2)}</td>
                    <td className="px-2 py-1 text-right text-yellow-300">{formatMetric(d.savings_opportunity_kwh, 2)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Machine comparison */}
      {compData.length > 0 && (
        <div className="rounded border border-gray-700 bg-gray-800 p-4">
          <h3 className="text-lg font-medium text-teal-200 mb-3">Per-Machine Energy Comparison</h3>
          <div className="overflow-x-auto">
            <table className="w-full text-sm text-gray-200">
              <thead className="border-b border-gray-700">
                <tr>
                  <th className="px-2 py-1 text-left text-gray-400">Machine</th>
                  <th className="px-2 py-1 text-right text-gray-400">Avg SEC (kWh/part)</th>
                  <th className="px-2 py-1 text-right text-gray-400">Total Energy (kWh)</th>
                  <th className="px-2 py-1 text-right text-gray-400">Est. Cost (₹)</th>
                  <th className="px-2 py-1 text-right text-gray-400">Est. CO₂ (tonnes)</th>
                </tr>
              </thead>
              <tbody>
                {compData.map((m) => (
                  <tr key={String(m.machine_id)} className="border-b border-gray-700 hover:bg-gray-700">
                    <td className="px-2 py-1 font-medium">{m.machine_name || m.machine_id || 'Unavailable'}</td>
                    <td className="px-2 py-1 text-right">{formatMetric(m.avg_sec_kwh_per_part, 4)}</td>
                    <td className="px-2 py-1 text-right">{formatMetric(m.total_energy_kwh, 2)}</td>
                    <td className="px-2 py-1 text-right text-yellow-300">{m.cost_inr == null || !Number.isFinite(m.cost_inr) ? 'Unavailable' : `₹${formatMetric(m.cost_inr, 0)}`}</td>
                    <td className="px-2 py-1 text-right text-green-300">{formatMetric(m.co2_tonnes, 3)}</td>
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
