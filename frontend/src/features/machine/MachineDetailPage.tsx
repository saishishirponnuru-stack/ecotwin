import React from 'react';
import { useParams, NavLink } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { getMachineDetail, getTelemetry } from '../../lib/api';
import type { MachineDetailResponse, TelemetryResponse } from '../../types/api';
import DailyEnergyChart from '../../components/charts/DailyEnergyChart';

function LoadingSpinner({ message }: { message?: string }) {
  return (
    <div className="flex flex-col items-center justify-center py-8 text-gray-300">
      <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-teal-400" />
      <p className="mt-2 text-sm">{message ?? 'Loading…'}</p>
    </div>
  );
}

function StatBadge({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="rounded border border-gray-700 bg-gray-900 p-3">
      <p className="text-xs text-gray-400 uppercase tracking-wide">{label}</p>
      <p className="mt-1 text-lg font-semibold text-teal-300">{value}</p>
    </div>
  );
}

export default function MachineDetailPage() {
  const { machineId } = useParams<{ machineId: string }>();

  const {
    data: detail,
    error: detailError,
    isLoading: detailLoading,
    refetch: refetchDetail,
  } = useQuery<MachineDetailResponse>({
    queryKey: ['machineDetail', machineId],
    queryFn: () => getMachineDetail(machineId!),
    enabled: !!machineId,
    staleTime: 5 * 60 * 1000,
  });

  const {
    data: telemetry,
    isLoading: telemetryLoading,
  } = useQuery<TelemetryResponse>({
    queryKey: ['telemetry', machineId],
    queryFn: () => getTelemetry(machineId!),
    enabled: !!machineId,
    staleTime: 5 * 60 * 1000,
  });

  const chartData = React.useMemo(() => {
    if (!telemetry) return { dates: [], actual: [], baseline: [] };
    return {
      dates: telemetry.timestamps ?? [],
      actual: telemetry.actual ?? [],
      baseline: telemetry.predicted ?? [],
    };
  }, [telemetry]);

  if (detailLoading || telemetryLoading) return <LoadingSpinner />;

  if (detailError) {
    return (
      <div className="p-4 text-red-400">
        <p>Error loading machine details.</p>
        <button className="mt-2 rounded bg-teal-600 px-3 py-1 hover:bg-teal-500" onClick={() => refetchDetail()}>
          Retry
        </button>
      </div>
    );
  }

  if (!detail) return <p className="p-4 text-gray-400">No data for this machine.</p>;

  const { machine, operating_stats, recent_readings, active_anomalies } = detail;

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <NavLink to="/machine" className="text-teal-400 hover:underline text-sm">← Fleet</NavLink>
        <h2 className="text-2xl font-semibold text-teal-300">Machine Detail — {machine.id}</h2>
      </div>

      {/* Identity */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <StatBadge label="Machine ID" value={machine.id} />
        <StatBadge label="Name" value={machine.name ?? '—'} />
        <StatBadge label="Status" value={machine.status} />
        <StatBadge label="Model" value={machine.model_type} />
        <StatBadge label="Rated Power" value={`${machine.rated_power_kw} kW`} />
      </div>

      {/* Operating stats */}
      <div className="rounded border border-gray-700 bg-gray-800 p-4">
        <h3 className="text-lg font-medium text-teal-200 mb-3">Operating Statistics</h3>
        <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
          {Object.entries(operating_stats).map(([k, v]) => (
            <StatBadge
              key={k}
              label={k.replace(/_/g, ' ')}
              value={typeof v === 'number' ? v.toFixed(3) : String(v)}
            />
          ))}
        </div>
      </div>

      {/* Telemetry Chart */}
      <div className="rounded border border-gray-700 bg-gray-800 p-4">
        <h3 className="text-lg font-medium text-teal-200 mb-2">Energy Telemetry</h3>
        {chartData.dates.length > 0 ? (
          <DailyEnergyChart data={chartData} comparisonLabel="Model prediction" />
        ) : (
          <p className="text-gray-400">No telemetry data available.</p>
        )}
      </div>

      {/* Recent readings */}
      {recent_readings && recent_readings.length > 0 && (
        <div className="rounded border border-gray-700 bg-gray-800 p-4">
          <h3 className="text-lg font-medium text-teal-200 mb-2">Recent Readings (last {recent_readings.length})</h3>
          <div className="overflow-x-auto">
            <table className="w-full text-sm text-gray-200">
              <thead className="border-b border-gray-700">
                <tr>
                  {Object.keys(recent_readings[0]).map((k) => (
                    <th key={k} className="px-2 py-1 text-left text-gray-400 font-medium">{k.replace(/_/g, ' ')}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {recent_readings.slice(0, 10).map((row, idx) => (
                  <tr key={idx} className="border-b border-gray-700 hover:bg-gray-700">
                    {Object.values(row).map((v, vi) => (
                      <td key={vi} className="px-2 py-1">
                        {typeof v === 'number' ? v.toFixed(3) : String(v ?? '—')}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Active Anomalies */}
      <div className="rounded border border-gray-700 bg-gray-800 p-4">
        <h3 className="text-lg font-medium text-teal-200 mb-2">Active Anomalies</h3>
        {active_anomalies && active_anomalies.length > 0 ? (
          <ul className="space-y-2">
            {active_anomalies.map((a, idx) => (
              <li key={idx} className="flex items-start gap-2 text-sm text-gray-200">
                <span className={`mt-0.5 rounded px-1.5 py-0.5 text-xs font-medium ${
                  String(a['severity']) === 'critical' ? 'bg-red-700 text-red-100' :
                  String(a['severity']) === 'warning' ? 'bg-yellow-700 text-yellow-100' :
                  'bg-blue-700 text-blue-100'
                }`}>{String(a['severity'] ?? 'watch').toUpperCase()}</span>
                <span>{String(a['reason_code'] ?? '—')}</span>
                <span className="text-gray-500">{String(a['timestamp'] ?? '')}</span>
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-gray-400">No active anomalies.</p>
        )}
      </div>
    </div>
  );
}
