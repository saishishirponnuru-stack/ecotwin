import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { getRecommendations } from '../../lib/api';
import type { RecommendationItem } from '../../types/api';

const DIFFICULTY_COLOR: Record<string, string> = {
  Low: 'bg-green-700 text-green-100',
  Medium: 'bg-yellow-700 text-yellow-100',
  High: 'bg-red-700 text-red-100',
};

const CATEGORY_COLOR: Record<string, string> = {
  'Energy Consumption': 'bg-blue-800 text-blue-200',
  Efficiency: 'bg-teal-800 text-teal-200',
  Reliability: 'bg-purple-800 text-purple-200',
};

export default function RecommendationsPage() {
  const { data, error, isLoading, refetch } = useQuery({
    queryKey: ['recommendations'],
    queryFn: getRecommendations,
    staleTime: 5 * 60 * 1000,
  });

  const [categoryFilter, setCategoryFilter] = React.useState('All');

  const categories = React.useMemo(() => {
    if (!data) return ['All'];
    const cats = Array.from(new Set(data.recommendations.map((r) => r.category)));
    return ['All', ...cats];
  }, [data]);

  const filtered = React.useMemo(() => {
    if (!data) return [] as RecommendationItem[];
    let recs = data.recommendations;
    if (categoryFilter !== 'All') recs = recs.filter((r) => r.category === categoryFilter);
    return recs;
  }, [data, categoryFilter]);

  const quantified = (value: unknown, unit?: string) =>
    typeof value === 'number' && Number.isFinite(value)
      ? `${value.toLocaleString(undefined, { maximumFractionDigits: 2 })}${unit ? ` ${unit}` : ''}`
      : 'Not quantified';

  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center py-16 text-gray-300">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-teal-400" />
        <p className="mt-3 text-sm">Loading recommendations…</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded border border-red-700 bg-red-900/30 p-4 text-red-300">
        <p className="font-medium">Failed to load recommendations.</p>
        <button className="mt-2 rounded bg-teal-600 px-3 py-1 text-sm hover:bg-teal-500" onClick={() => refetch()}>
          Retry
        </button>
      </div>
    );
  }

  if (!data || data.recommendations.length === 0) {
    return (
      <div className="rounded border border-gray-700 bg-gray-800 p-8 text-center text-gray-400">
        No recommendations generated yet. Add more telemetry data to unlock insights.
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div>
          <h2 className="text-2xl font-semibold text-teal-300">Evidence-Based Recommendations</h2>
          <p className="text-sm text-gray-400 mt-0.5">
            {filtered.length} of {data.recommendations.length} recommendations shown ·{' '}
            <span className="text-yellow-400">Rules identify investigation priorities; benefits are not quantified without a validated baseline.</span>
          </p>
        </div>
        <div className="flex gap-2 flex-wrap">
          <select
            className="rounded border border-gray-600 bg-gray-800 px-2 py-1 text-sm text-gray-200"
            value={categoryFilter}
            onChange={(e) => setCategoryFilter(e.target.value)}
          >
            {categories.map((c) => <option key={c}>{c}</option>)}
          </select>
          <button
            className="rounded border border-gray-600 bg-gray-700 px-2 py-1 text-sm text-gray-200 hover:bg-gray-600"
            onClick={() => refetch()}
          >
            Refresh
          </button>
        </div>
      </div>

      <div className="space-y-4">
        {filtered.map((rec) => (
          <div key={rec.id} className="rounded border border-gray-700 bg-gray-800 p-4 space-y-3">
            <div className="flex flex-wrap items-start gap-2">
              <span className={`rounded px-2 py-0.5 text-xs font-medium ${CATEGORY_COLOR[rec.category] ?? 'bg-gray-700 text-gray-200'}`}>
                {rec.category}
              </span>
              {rec.machine_id && (
                <span className="rounded border border-teal-700 px-2 py-0.5 text-xs text-teal-300">
                  Machine: {rec.machine_id}
                </span>
              )}
              <span className={`ml-auto rounded px-2 py-0.5 text-xs font-medium ${DIFFICULTY_COLOR[rec.difficulty] ?? 'bg-gray-700 text-gray-200'}`}>
                {rec.difficulty} Difficulty
              </span>
            </div>

            <div>
              <p className="font-medium text-gray-100">{rec.action}</p>
              <p className="text-sm text-gray-400 mt-1">{rec.reason}</p>
            </div>

            <div className="grid grid-cols-3 gap-3">
              <div className="rounded bg-gray-900 p-2 text-center">
                <p className="text-xs text-gray-500">Energy benefit</p>
                <p className="font-semibold text-teal-300">{quantified(rec.expected_benefit.energy_kwh, 'kWh')}</p>
              </div>
              <div className="rounded bg-gray-900 p-2 text-center">
                <p className="text-xs text-gray-500">Cost benefit</p>
                <p className="font-semibold text-yellow-300">{typeof rec.expected_benefit.cost_inr === 'number' ? `₹${quantified(rec.expected_benefit.cost_inr)}` : 'Not quantified'}</p>
              </div>
              <div className="rounded bg-gray-900 p-2 text-center">
                <p className="text-xs text-gray-500">Emissions benefit</p>
                <p className="font-semibold text-green-300">{typeof rec.expected_benefit.co2_tonnes === 'number' ? quantified(rec.expected_benefit.co2_tonnes * 1000, 'kg CO₂e') : 'Not quantified'}</p>
              </div>
            </div>

            <div className="rounded border border-gray-700 bg-gray-900/50 p-2">
              <p className="text-xs font-medium text-gray-300">Evidence — {rec.evidence_source}</p>
              <p className="mt-1 text-xs text-gray-400">{rec.evidence_summary}</p>
            </div>

            {rec.assumptions && (
              <p className="text-xs text-gray-500 italic">
                ⚠ Assumption: {rec.assumptions}
              </p>
            )}
            <p className="text-xs text-gray-600">Provenance: {rec.provenance}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
