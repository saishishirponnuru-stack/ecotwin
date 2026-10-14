import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { getOverview } from '../../lib/api';
import { OverviewResponse } from '../../types/api';
import { OverviewCard } from './OverviewCard';
import { LoadingState } from '../../components/ui/LoadingState';
import { ErrorState } from '../../components/ui/ErrorState';
import DailyEnergyChart from '../../components/charts/DailyEnergyChart';
import MachinePerformanceChart from '../../components/charts/MachinePerformanceChart';

export default function OverviewPage() {
  const {
    data,
    isLoading,
    isError,
    error,
    refetch,
  } = useQuery<OverviewResponse>({
    queryKey: ['overview'],
    queryFn: getOverview,
    retry: false,
  });

  if (isLoading) {
    return <LoadingState />;
  }

  if (isError) {
    const message = error instanceof Error ? error.message : 'Failed to load overview data';
    return <ErrorState message={message} onRetry={refetch} />;
  }

  const overview = data!;

  // Values are computed from stored demonstration telemetry, not live readings.
  const provenanceMap: Record<string, number[]> = {
    facility_health_score: [3],
    avg_sec_kwh_per_part: [2],
    total_energy_kwh: [2],
    total_anomalies: [4],
    est_co2_tonnes: [2],
  };

// Parse daily trend data safely, handling both array and legacy JSON string formats
let dailyChartData = null;
if (Array.isArray(overview.daily_trend) && overview.daily_trend.length) {
  dailyChartData = {
    dates: overview.daily_trend.map(d => d.date),
    actual: overview.daily_trend.map(d => d.actual_kwh),
    baseline: overview.daily_trend.map(d => d.baseline_kwh),
  };
}

  // Machine performance data from fleet_summary
  const machines = overview.fleet_summary?.map(m => ({
      id: m.id,
      avg_sec: m.avg_sec,
    })) ?? [];

  // Helper to format numbers with fallback em‑dash
  const formatNumber = (value: number | undefined, opts: { unit?: string; digits?: number } = {}) => {
    if (value == null || Number.isNaN(value)) return '—';
    const { unit = '', digits = 2 } = opts;
    return `${value.toFixed(digits)}${unit && ' '}${unit}`.trim();
  };

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-semibold text-teal-300">Executive Command Center</h2>
        <p className="mt-1 text-sm text-gray-400">
          Reporting period: {overview.reporting_window ?? 'Unavailable'} · Historical demonstration telemetry, not live data.
        </p>
      </div>
      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        <OverviewCard
          title="Operational Indicator"
          value={formatNumber(overview.facility_health_score, { unit: '%', digits: 2 })}
          description="Internal indicator based on anomaly rate; not a validated equipment-health score."
          provenance={provenanceMap.facility_health_score}
        />
        <OverviewCard
          title="Energy Intensity"
          value={formatNumber(overview.avg_sec_kwh_per_part, { unit: 'kWh/part', digits: 3 })}
          description="Total derived energy divided by recorded completed parts."
          provenance={provenanceMap.avg_sec_kwh_per_part}
        />
        <OverviewCard
          title="Total Energy"
          value={formatNumber(overview.total_energy_kwh, { unit: 'kWh', digits: 0 })}
          description="Derived from torque, speed, cycle time, and assumed motor efficiency."
          provenance={provenanceMap.total_energy_kwh}
        />
        <OverviewCard
          title="Logged Anomalies"
          value={overview.total_anomalies?.toString() ?? '—'}
          provenance={provenanceMap.total_anomalies}
        />
        <OverviewCard
          title="Estimated CO₂e Emissions"
          value={formatNumber(overview.est_co2_tonnes, { unit: 'tonnes', digits: 2 })}
          description="Energy multiplied by the configured grid-emissions factor."
          provenance={provenanceMap.est_co2_tonnes}
        />
      </div>

      {/* Daily Energy Chart */}
      {dailyChartData ? (
        <DailyEnergyChart data={dailyChartData} />
      ) : (
        <ErrorState message="No daily chart data available" onRetry={refetch} />
      )}

      {/* Machine Performance */}
      <div className="bg-gray-800 rounded-lg p-4 shadow-md">
        <h2 className="text-lg font-medium text-gray-200 mb-4">Machine Performance</h2>
        <MachinePerformanceChart machines={machines} />
      </div>
    </div>
  );
}
