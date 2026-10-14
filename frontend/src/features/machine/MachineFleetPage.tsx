import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { getMachines, getOverview } from '../../lib/api';
import { NavLink } from 'react-router-dom';
import type { MachineResponse, OverviewResponse } from '../../types/api';

function formatMetric(value: number | null | undefined, suffix = '') {
  return typeof value === 'number' && Number.isFinite(value)
    ? `${value.toFixed(2)}${suffix}`
    : 'Unavailable';
}

function formatCount(value: number | null | undefined) {
  return typeof value === 'number' && Number.isFinite(value) ? value : 'Unavailable';
}

function LoadingSpinner({ message }: { message?: string }) {
  return (
    <div className="flex flex-col items-center justify-center py-8 text-gray-300">
      <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-teal-400" />
      <p className="mt-2 text-sm">{message ?? 'Loading…'}</p>
    </div>
  );
}

export default function MachineFleetPage() {
  const {
    data: machines,
    error,
    isLoading,
    refetch,
  } = useQuery<MachineResponse[]>({
    queryKey: ['machines'],
    queryFn: getMachines,
    staleTime: 5 * 60 * 1000,
  });
  const { data: overview } = useQuery<OverviewResponse>({
    queryKey: ['overview'],
    queryFn: getOverview,
    staleTime: 5 * 60 * 1000,
  });

  const [filter, setFilter] = React.useState('');
  const fleetMetrics = React.useMemo(
    () => new Map(overview?.fleet_summary.map((item) => [item.id, item]) ?? []),
    [overview],
  );
  const filtered = React.useMemo(() => {
    if (!machines) return [] as MachineResponse[];
    const term = filter.toLowerCase();
    return machines.filter((m) => {
      const id = m.id.toLowerCase();
      const name = (m.name ?? '').toString().toLowerCase();
      return id.includes(term) || name.includes(term);
    });
  }, [machines, filter]);

  if (isLoading) return <LoadingSpinner />;
  if (error) {
    return (
      <div className="p-4 text-red-400">
        <p>Error loading machines.</p>
        <button className="mt-2 rounded bg-teal-600 px-3 py-1 hover:bg-teal-500" onClick={() => refetch()}>
          Retry
        </button>
      </div>
    );
  }

  if (!machines || machines.length === 0) {
    return <p className="p-4 text-gray-400">No machines found.</p>;
  }

  return (
    <div className="space-y-4">
      <h2 className="text-xl font-semibold text-teal-300">Machine Fleet</h2>
      <p className="text-xs text-gray-400">
        SEC is derived per machine from recorded telemetry. Efficiency is the API's derived indicator, not a directly measured equipment-efficiency value.
      </p>
      <input
        type="text"
        placeholder="Search by ID or name"
        className="rounded border border-gray-600 bg-gray-800 p-2 text-gray-100 placeholder-gray-500"
        value={filter}
        onChange={(e) => setFilter(e.target.value)}
      />
      <div className="overflow-x-auto">
        <table className="w-full text-left text-gray-200">
          <thead className="border-b border-gray-700 bg-gray-800">
            <tr>
              <th className="px-2 py-1">ID</th>
              <th className="px-2 py-1">Name</th>
              <th className="px-2 py-1">Status</th>
              <th className="px-2 py-1">Efficiency</th>
              <th className="px-2 py-1">SEC (kWh/part)</th>
              <th className="px-2 py-1">Anomalies</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((machine) => (
              <tr key={machine.id} className="border-b border-gray-700 hover:bg-gray-700">
                <td className="px-2 py-1">
                  <NavLink to={`/machine/${encodeURIComponent(machine.id)}`} className="text-teal-400 hover:underline">
                    {machine.id}
                  </NavLink>
                </td>
                <td className="px-2 py-1">{machine.name}</td>
                <td className="px-2 py-1">{machine.status}</td>
                <td className="px-2 py-1">{formatMetric(fleetMetrics.get(machine.id)?.efficiency_score, '%')}</td>
                <td className="px-2 py-1">{formatMetric(fleetMetrics.get(machine.id)?.avg_sec)} kWh/part</td>
                <td className="px-2 py-1">{formatCount(fleetMetrics.get(machine.id)?.total_anomalies)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
