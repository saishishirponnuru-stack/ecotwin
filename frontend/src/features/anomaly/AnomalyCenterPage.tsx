import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { getAnomalies, resolveAnomaly } from '../../lib/api';
import type { AnomalyItem } from '../../types/api';
import { useMutation, useQueryClient } from '@tanstack/react-query';

const SEVERITY_COLOR: Record<string, string> = {
  critical: 'bg-red-700 text-red-100',
  warning: 'bg-yellow-700 text-yellow-100',
  watch: 'bg-blue-700 text-blue-100',
};

function AnomalyRow({
  anomaly,
  onResolve,
  resolving,
}: {
  anomaly: AnomalyItem;
  onResolve: (id: number) => void;
  resolving: boolean;
}) {
  return (
    <tr className="border-b border-gray-700 hover:bg-gray-700">
      <td className="px-3 py-2">
        <span className={`rounded px-1.5 py-0.5 text-xs font-medium ${SEVERITY_COLOR[anomaly.severity] ?? 'bg-gray-700 text-gray-200'}`}>
          {anomaly.severity.toUpperCase()}
        </span>
      </td>
      <td className="px-3 py-2 text-sm text-gray-200">{anomaly.machine_id}</td>
      <td className="px-3 py-2 text-sm text-gray-300">{anomaly.reason_code}</td>
      <td className="px-3 py-2 text-sm text-gray-400">{new Date(anomaly.timestamp).toLocaleString()}</td>
      <td className="px-3 py-2 text-sm text-right text-yellow-300">{anomaly.actual_kwh.toFixed(2)}</td>
      <td className="px-3 py-2 text-sm text-right text-teal-300">{anomaly.predicted_kwh.toFixed(2)}</td>
      <td className="px-3 py-2 text-sm text-right text-orange-300">{anomaly.potential_saving_kwh.toFixed(2)}</td>
      <td className="px-3 py-2 text-center">
        {anomaly.is_resolved ? (
          <span className="text-xs text-gray-500">Resolved</span>
        ) : (
          <button
            disabled={resolving}
            onClick={() => onResolve(anomaly.id)}
            className="rounded bg-teal-700 px-2 py-0.5 text-xs hover:bg-teal-600 disabled:opacity-50"
          >
            Resolve
          </button>
        )}
      </td>
    </tr>
  );
}

export default function AnomalyCenterPage() {
  const [machineFilter, setMachineFilter] = React.useState('');
  const [severityFilter, setSeverityFilter] = React.useState('');
  const [resolutionFilter, setResolutionFilter] = React.useState('open');
  const [resolvingId, setResolvingId] = React.useState<number | null>(null);
  const queryClient = useQueryClient();

  const { data, error, isLoading, refetch } = useQuery({
    queryKey: ['anomalies', machineFilter, severityFilter, resolutionFilter],
    queryFn: () => getAnomalies({
      machine_id: machineFilter || undefined,
      severity: severityFilter || undefined,
      is_resolved: resolutionFilter === 'all' ? undefined : resolutionFilter === 'resolved',
      limit: 100,
    }),
    staleTime: 2 * 60 * 1000,
  });

  const resolveMutation = useMutation({
    mutationFn: ({ id, notes }: { id: number; notes: string }) => resolveAnomaly(id, notes),
    onMutate: ({ id }) => setResolvingId(id),
    onSettled: () => {
      setResolvingId(null);
      queryClient.invalidateQueries({ queryKey: ['anomalies'] });
    },
  });

  const machines = React.useMemo(() => {
    if (!data) return [] as string[];
    return Array.from(new Set(data.anomalies.map((a) => a.machine_id))).sort();
  }, [data]);

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div>
          <h2 className="text-2xl font-semibold text-teal-300">Anomaly Center</h2>
          {data && (
            <p className="text-sm text-gray-400 mt-0.5">
              {data.total_count} total ·{' '}
              <span className="text-red-400">{data.critical_count} critical</span> ·{' '}
              <span className="text-yellow-400">{data.warning_count} warning</span> ·{' '}
              <span className="text-blue-400">{data.watch_count} watch</span>
            </p>
          )}
        </div>
        <div className="flex gap-2 flex-wrap">
          <select
            className="rounded border border-gray-600 bg-gray-800 px-2 py-1 text-sm text-gray-200"
            value={machineFilter}
            onChange={(e) => setMachineFilter(e.target.value)}
          >
            <option value="">All Machines</option>
            {machines.map((m) => <option key={m} value={m}>{m}</option>)}
          </select>
          <select
            aria-label="Filter by resolution status"
            className="rounded border border-gray-600 bg-gray-800 px-2 py-1 text-sm text-gray-200"
            value={resolutionFilter}
            onChange={(e) => setResolutionFilter(e.target.value)}
          >
            <option value="open">Open</option>
            <option value="resolved">Resolved</option>
            <option value="all">All statuses</option>
          </select>
          <select
            className="rounded border border-gray-600 bg-gray-800 px-2 py-1 text-sm text-gray-200"
            value={severityFilter}
            onChange={(e) => setSeverityFilter(e.target.value)}
          >
            <option value="">All Severities</option>
            <option value="critical">Critical</option>
            <option value="warning">Warning</option>
            <option value="watch">Watch</option>
          </select>
          <button
            className="rounded border border-gray-600 bg-gray-700 px-2 py-1 text-sm text-gray-200 hover:bg-gray-600"
            onClick={() => refetch()}
          >
            Refresh
          </button>
        </div>
      </div>

      {isLoading && (
        <div className="flex items-center justify-center py-12 text-gray-300">
          <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-teal-400" />
        </div>
      )}

      {error && (
        <div className="rounded border border-red-700 bg-red-900/30 p-4 text-red-300">
          Failed to load anomalies.
          <button className="ml-3 rounded bg-teal-600 px-2 py-0.5 text-sm hover:bg-teal-500" onClick={() => refetch()}>Retry</button>
        </div>
      )}

      {data && data.anomalies.length === 0 && (
        <div className="rounded border border-gray-700 bg-gray-800 p-8 text-center text-gray-400">
          No anomalies match the current filters.
        </div>
      )}

      {data && data.anomalies.length > 0 && (
        <div className="rounded border border-gray-700 overflow-x-auto">
          <table className="w-full text-left text-gray-200">
            <thead className="border-b border-gray-700 bg-gray-800">
              <tr>
                <th className="px-3 py-2 text-xs text-gray-400">Severity</th>
                <th className="px-3 py-2 text-xs text-gray-400">Machine</th>
                <th className="px-3 py-2 text-xs text-gray-400">Reason</th>
                <th className="px-3 py-2 text-xs text-gray-400">Timestamp</th>
                <th className="px-3 py-2 text-xs text-gray-400 text-right">Actual kWh</th>
                <th className="px-3 py-2 text-xs text-gray-400 text-right">Predicted kWh</th>
                <th className="px-3 py-2 text-xs text-gray-400 text-right">Residual kWh</th>
                <th className="px-3 py-2 text-xs text-gray-400 text-center">Action</th>
              </tr>
            </thead>
            <tbody>
              {data.anomalies.map((a) => (
                <AnomalyRow
                  key={a.id}
                  anomaly={a}
                  onResolve={(id) => resolveMutation.mutate({ id, notes: 'Resolved via Anomaly Center UI' })}
                  resolving={resolvingId === a.id}
                />
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
