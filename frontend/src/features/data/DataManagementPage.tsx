import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { getMachines, getAnomalies } from '../../lib/api';
import type { MachineResponse } from '../../types/api';

/**
 * Data Management page.
 * Shows the current state of data in the system — machine count, telemetry
 * records, anomaly records — and provides a simple dataset overview.
 * File import is not supported by the current backend; this is disclosed.
 */

interface DatasetCard {
  title: string;
  count: number | string;
  description: string;
  provenance?: string;
}

function Card({ title, count, description, provenance }: DatasetCard) {
  return (
    <div className="rounded border border-gray-700 bg-gray-800 p-4 space-y-2">
      <div className="flex items-center justify-between">
        <h3 className="font-medium text-teal-300">{title}</h3>
        <span className="text-2xl font-bold text-white">{count}</span>
      </div>
      <p className="text-sm text-gray-400">{description}</p>
      {provenance && (
        <p className="text-xs text-gray-600">Provenance: {provenance}</p>
      )}
    </div>
  );
}

export default function DataManagementPage() {
  const { data: machines } = useQuery<MachineResponse[]>({
    queryKey: ['machines'],
    queryFn: getMachines,
    staleTime: 5 * 60 * 1000,
  });

  const { data: anomalies } = useQuery({
    queryKey: ['anomalies', '', ''],
    queryFn: () => getAnomalies({ limit: 500 }),
    staleTime: 5 * 60 * 1000,
  });

  const machineCount = machines?.length ?? '—';
  const anomalyCount = anomalies?.total_count ?? '—';
  const resolvedCount = anomalies ? anomalies.anomalies.filter((a) => a.is_resolved).length : '—';

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-semibold text-teal-300">Data Management</h2>
        <p className="text-sm text-gray-400 mt-0.5">
          Overview of datasets currently loaded in the EcoTwin system.
        </p>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <Card
          title="Machines"
          count={machineCount}
          description="CNC machines registered in the system with rated power and model metadata."
          provenance="Static configuration database"
        />
        <Card
          title="Anomalies Detected"
          count={anomalyCount}
          description="Statistical energy anomalies detected by the monitoring engine."
          provenance="Computed from telemetry — TIER_2 / TIER_3"
        />
        <Card
          title="Anomalies Resolved"
          count={resolvedCount}
          description="Anomalies marked as resolved by operators."
          provenance="Operator-entered resolution notes"
        />
      </div>

      <div className="rounded border border-yellow-700 bg-yellow-900/20 p-4 space-y-2">
        <p className="text-sm font-medium text-yellow-300">Import Not Supported</p>
        <p className="text-sm text-gray-400">
          The current backend does not expose a file import endpoint. Telemetry data is
          seeded programmatically via the database initialization script.
          To add new data, update the seed script at <code className="text-teal-300">scripts/seed_data.py</code> (or equivalent)
          and restart the backend.
        </p>
      </div>

      <div className="rounded border border-gray-700 bg-gray-800 p-4 space-y-3">
        <h3 className="text-lg font-medium text-teal-200">Data Provenance Tiers</h3>
        <ul className="space-y-2 text-sm text-gray-300">
          {[
            ['TIER_1_DIRECT_MEASUREMENT', 'Direct sensor readings — highest fidelity.'],
            ['TIER_2_PHYSICALLY_DERIVED', 'Computed from physics models using direct measurements.'],
            ['TIER_3_CALIBRATED_CONTEXT', 'Context-enriched derivations (anomaly flags, SEC comparisons).'],
            ['TIER_4_HEURISTIC_ESTIMATE', 'Rule-based heuristics; lower confidence.'],
            ['TIER_5_EXTRAPOLATED', 'Statistical extrapolations; use with caution.'],
          ].map(([tier, desc]) => (
            <li key={tier} className="flex gap-3">
              <span className="rounded bg-gray-900 px-1.5 py-0.5 text-xs font-mono text-teal-300 whitespace-nowrap">{tier}</span>
              <span className="text-gray-400">{desc}</span>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
