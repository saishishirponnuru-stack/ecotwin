import React from 'react';

interface ProvenanceBadgeProps {
  tier: number; // 1‑5
}

const tierColors: Record<number, string> = {
  1: 'bg-gray-500',
  2: 'bg-blue-500',
  3: 'bg-teal-500',
  4: 'bg-emerald-500',
  5: 'bg-yellow-500',
};

export const ProvenanceBadge: React.FC<ProvenanceBadgeProps> = ({ tier }) => {
  const bg = tierColors[tier] || 'bg-gray-400';
  return (
    <span
      className={`${bg} text-xs font-medium text-white px-1.5 py-0.5 rounded`}
      title={`Provenance tier ${tier}`}
    >
      T{tier}
    </span>
  );
};
