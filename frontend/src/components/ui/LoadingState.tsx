import React from 'react';

export const LoadingState: React.FC = () => (
  <div role="status" aria-live="polite" className="flex min-h-64 flex-col items-center justify-center gap-4 px-4 text-center text-gray-400">
    <div className="flex items-center gap-3">
      <img className="h-12 w-12 rounded-xl bg-slate-950 p-1.5" src="/ecotwin-mark-64.png" alt="" />
      <span className="text-lg font-semibold text-teal-300">EcoTwin</span>
      <svg className="h-6 w-6 animate-spin text-teal-400" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" aria-hidden="true">
        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z"></path>
      </svg>
    </div>
    <p className="max-w-md text-sm">Connecting to EcoTwin's demo service. The free hosting instance may take a moment to start.</p>
    <p className="max-w-md text-xs text-gray-500">The dashboard uses stored demonstration data, not live telemetry.</p>
  </div>
);
