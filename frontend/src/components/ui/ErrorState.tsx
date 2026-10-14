import React from 'react';

interface ErrorStateProps {
  message: string;
  onRetry: () => void;
}

export const ErrorState: React.FC<ErrorStateProps> = ({ message, onRetry }) => (
  <div className="flex flex-col items-center justify-center h-64 text-red-400">
    <p className="mb-4">{message}</p>
    <button
      onClick={onRetry}
      className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded"
    >
      Retry
    </button>
  </div>
);
