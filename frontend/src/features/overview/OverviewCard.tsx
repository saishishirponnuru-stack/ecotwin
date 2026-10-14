import React from 'react';
import { ProvenanceBadge } from '../../components/ui/ProvenanceBadge';

interface OverviewCardProps {
  title: string;
  value: string | number;
  unit?: string;
  description?: string;
  provenance?: number[]; // array of tier numbers (1‑5)
}

export const OverviewCard: React.FC<OverviewCardProps> = ({
  title,
  value,
  unit = '',
  description = '',
  provenance = [],
}) => {
  return (
    <div className="bg-gray-800 rounded-lg p-4 shadow-md flex flex-col justify-between">
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-sm font-medium text-gray-300">{title}</h3>
        {provenance.length > 0 && (
          <div className="flex space-x-1">
            {provenance.map(t => (
              <ProvenanceBadge key={t} tier={t} />
            ))}
          </div>
        )}
      </div>
      <div className="text-2xl font-semibold text-teal-300">
        {value}{unit && <span className="text-sm font-medium text-gray-400"> {unit}</span>}
      </div>
      {description && (
        <p className="mt-1 text-xs text-gray-500">{description}</p>
      )}
    </div>
  );
};
