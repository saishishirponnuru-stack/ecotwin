import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { getEnergyOverview, getRecommendations, getAnomalies } from '../../lib/api';

/**
 * Reports page.
 * Provides a downloadable JSON summary of the facility's energy, anomaly,
 * and recommendation status. A dedicated CSV export endpoint does not exist
 * yet in the backend; this is disclosed.
 */

export default function ReportsPage() {
  const { data: overview } = useQuery({
    queryKey: ['energyOverview'],
    queryFn: getEnergyOverview,
    staleTime: 5 * 60 * 1000,
  });

  const { data: recommendations } = useQuery({
    queryKey: ['recommendations'],
    queryFn: getRecommendations,
    staleTime: 5 * 60 * 1000,
  });

  const { data: anomalies } = useQuery({
    queryKey: ['anomalies', '', ''],
    queryFn: () => getAnomalies({ limit: 500 }),
    staleTime: 5 * 60 * 1000,
  });

  const [generating, setGenerating] = React.useState(false);
  const [lastGenerated, setLastGenerated] = React.useState<string | null>(null);

  const handleDownload = () => {
    setGenerating(true);
    const report = {
      generated_at: new Date().toISOString(),
      label: 'EcoTwin Facility Report — JSON Summary',
      provenance_note: 'All benefit figures are heuristic estimates unless otherwise noted. No verified savings data available.',
      energy_overview: overview ?? null,
      anomaly_summary: anomalies
        ? {
            total: anomalies.total_count,
            critical: anomalies.critical_count,
            warning: anomalies.warning_count,
            watch: anomalies.watch_count,
            resolved: anomalies.anomalies.filter((a) => a.is_resolved).length,
          }
        : null,
      recommendations_count: recommendations?.recommendations.length ?? 0,
      recommendations: recommendations?.recommendations ?? [],
    };

    const blob = new Blob([JSON.stringify(report, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `ecotwin-report-${new Date().toISOString().slice(0, 10)}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);

    setLastGenerated(new Date().toLocaleTimeString());
    setGenerating(false);
  };

  const ready = !!(overview && recommendations && anomalies);

  return (
    <div className="space-y-6 max-w-2xl">
      <div>
        <h2 className="text-2xl font-semibold text-teal-300">Reports</h2>
        <p className="text-sm text-gray-400 mt-0.5">
          Generate and download facility reports from the currently stored API data.
        </p>
      </div>

      <div className="rounded border border-gray-700 bg-gray-800 p-4 space-y-4">
        <h3 className="text-lg font-medium text-teal-200">Facility Energy Summary</h3>
        <p className="text-sm text-gray-400">
          JSON report containing: energy overview KPIs, anomaly summary (totals by severity and resolution status),
          and all generated recommendations with their evidence and assumptions.
        </p>

        {ready && overview && (
          <div className="grid grid-cols-2 gap-3 text-sm">
            <div className="rounded bg-gray-900 p-2">
              <p className="text-gray-400">Total Energy</p>
              <p className="font-medium text-teal-300">{overview.total_energy_kwh.toFixed(1)} kWh</p>
            </div>
            <div className="rounded bg-gray-900 p-2">
              <p className="text-gray-400">Anomalies</p>
              <p className="font-medium text-red-300">{anomalies?.total_count ?? 0} total</p>
            </div>
            <div className="rounded bg-gray-900 p-2">
              <p className="text-gray-400">Recommendations</p>
              <p className="font-medium text-yellow-300">{recommendations?.recommendations.length ?? 0}</p>
            </div>
            <div className="rounded bg-gray-900 p-2">
              <p className="text-gray-400">Health Score</p>
              <p className="font-medium text-teal-300">{overview.facility_health_score.toFixed(1)}%</p>
            </div>
          </div>
        )}

        <button
          onClick={handleDownload}
          disabled={!ready || generating}
          className="rounded bg-teal-600 px-4 py-2 text-sm font-medium text-white hover:bg-teal-500 disabled:opacity-50"
        >
          {!ready ? 'Loading data…' : generating ? 'Generating…' : '⬇ Download JSON Report'}
        </button>

        {lastGenerated && (
          <p className="text-xs text-green-400">Last downloaded at {lastGenerated}</p>
        )}
      </div>

      <div className="rounded border border-yellow-700 bg-yellow-900/20 p-4">
        <p className="text-sm font-medium text-yellow-300">CSV / PDF Export</p>
        <p className="text-sm text-gray-400 mt-1">
          The backend does not currently expose a <code className="text-teal-300">GET /api/v1/report</code> endpoint
          with CSV output. The JSON download above is generated client-side from live API data.
          A server-side CSV endpoint can be added to <code className="text-teal-300">src/api/v1/reports.py</code> in a future iteration.
        </p>
      </div>
    </div>
  );
}
