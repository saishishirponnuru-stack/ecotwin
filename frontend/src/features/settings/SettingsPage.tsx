import React from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getConfig, resetDemoData, updateConfig } from '../../lib/api';
import type { ConfigItem, DemoDataResetResponse } from '../../types/api';
import { useTheme } from '../../theme/useTheme';

export default function SettingsPage() {
  const { theme, setTheme } = useTheme();
  const queryClient = useQueryClient();
  const [resetDialogOpen, setResetDialogOpen] = React.useState(false);
  const [resetSuccessMessage, setResetSuccessMessage] = React.useState('');
  const { data: configItems, error, isLoading, refetch } = useQuery<ConfigItem[]>({
    queryKey: ['config'],
    queryFn: getConfig,
    staleTime: 60 * 1000,
  });

  const [edits, setEdits] = React.useState<Record<string, string> | null>(null);
  const [saveStatus, setSaveStatus] = React.useState<'idle' | 'saving' | 'saved' | 'error'>('idle');
  const configuredValues = Object.fromEntries((configItems ?? []).map((item) => [item.key, item.value]));
  const currentEdits = edits ?? configuredValues;

  const saveMutation = useMutation({
    mutationFn: () => updateConfig(currentEdits),
    onMutate: () => setSaveStatus('saving'),
    onSuccess: () => {
      setSaveStatus('saved');
      setEdits(null);
      refetch();
      setTimeout(() => setSaveStatus('idle'), 3000);
    },
    onError: () => setSaveStatus('error'),
  });

  const resetMutation = useMutation<DemoDataResetResponse, Error>({
    mutationFn: resetDemoData,
    onSuccess: (result) => {
      setResetDialogOpen(false);
      const backupMessage = result.backup_file ? ` Backup saved to ${result.backup_file}.` : '';
      setResetSuccessMessage(`${result.message} ${result.updated_count} status flag(s) changed.${backupMessage}`);
      void queryClient.invalidateQueries({ queryKey: ['anomalies'] });
      void queryClient.invalidateQueries({ queryKey: ['overview'] });
      void queryClient.invalidateQueries({ queryKey: ['machineDetail'] });
    },
  });

  const hasChanges = configItems?.some((c) => currentEdits[c.key] !== c.value);

  return (
    <div className="space-y-6 max-w-2xl">
      <div>
        <h2 className="text-2xl font-semibold text-teal-300">Settings</h2>
        <p className="text-sm text-gray-400 mt-0.5">
          Manage your local appearance preference and energy-analysis configuration separately.
        </p>
      </div>

      <section aria-labelledby="appearance-heading" className="rounded border border-gray-700 bg-gray-800 p-4 space-y-3">
        <div>
          <h3 id="appearance-heading" className="text-lg font-medium text-teal-200">Appearance</h3>
          <p className="text-sm text-gray-400">Choose the interface theme. This preference is stored in this browser and does not change energy settings.</p>
        </div>
        <fieldset>
          <legend className="mb-2 text-sm font-medium text-gray-200">Color theme</legend>
          <div className="flex flex-wrap gap-3">
            <label htmlFor="ecotwin-theme-dark" className="flex cursor-pointer items-center gap-2 rounded border border-gray-600 px-3 py-2 text-sm text-gray-200 hover:bg-gray-700">
              <input id="ecotwin-theme-dark" type="radio" name="ecotwin-theme" value="dark" checked={theme === 'dark'} onChange={() => setTheme('dark')} />
              Dark
            </label>
            <label htmlFor="ecotwin-theme-light" className="flex cursor-pointer items-center gap-2 rounded border border-gray-600 px-3 py-2 text-sm text-gray-200 hover:bg-gray-700">
              <input id="ecotwin-theme-light" type="radio" name="ecotwin-theme" value="light" checked={theme === 'light'} onChange={() => setTheme('light')} />
              Light
            </label>
          </div>
        </fieldset>
        <p role="status" aria-live="polite" className="text-sm text-gray-400">{theme === 'dark' ? 'Dark' : 'Light'} theme active. Preference saved on this device.</p>
      </section>

      <section aria-labelledby="demo-data-heading" className="rounded border border-gray-700 bg-gray-800 p-4 space-y-3">
        <div>
          <h3 id="demo-data-heading" className="text-lg font-medium text-teal-200">Demo &amp; Data Management</h3>
          <p className="text-sm text-gray-400">Restore the original seeded anomaly demonstration state without resetting the database.</p>
        </div>
        <button
          type="button"
          onClick={() => {
            resetMutation.reset();
            setResetSuccessMessage('');
            setResetDialogOpen(true);
          }}
          className="rounded border border-red-700 bg-red-900/30 px-4 py-2 text-sm font-medium text-red-200 hover:bg-red-900/60"
        >
          Reset Demo Data
        </button>
        {resetSuccessMessage && <p role="status" aria-live="polite" className="text-sm text-green-300">{resetSuccessMessage}</p>}
      </section>

      {resetDialogOpen && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4"
          onKeyDown={(event) => {
            if (event.key === 'Escape' && !resetMutation.isPending) {
              setResetDialogOpen(false);
              resetMutation.reset();
            }
            if (event.key === 'Tab') {
              const buttons = Array.from(event.currentTarget.querySelectorAll<HTMLButtonElement>('button:not([disabled])'));
              const firstButton = buttons[0];
              const lastButton = buttons[buttons.length - 1];
              if (event.shiftKey && document.activeElement === firstButton) {
                event.preventDefault();
                lastButton?.focus();
              } else if (!event.shiftKey && document.activeElement === lastButton) {
                event.preventDefault();
                firstButton?.focus();
              }
            }
          }}
        >
          <section
            role="alertdialog"
            aria-modal="true"
            aria-labelledby="reset-demo-title"
            aria-describedby="reset-demo-description"
            className="w-full max-w-lg space-y-4 rounded border border-red-700 bg-gray-900 p-5 shadow-xl"
          >
            <div>
              <h3 id="reset-demo-title" className="text-lg font-semibold text-red-200">Confirm Reset Demo Data</h3>
              <p id="reset-demo-description" className="mt-2 text-sm text-gray-200">
                This will restore the 20 original seeded anomaly events to open/unresolved. Resolved demo records will be reopened; their IDs, timestamps, telemetry, readings, severity, and metadata will be preserved.
              </p>
              <p className="mt-2 text-sm text-gray-400">
                No records will be created or deleted. Machine configuration, energy settings and formulas, saved scenarios, historical/imported telemetry, model artifacts, and your theme preference will not be changed.
              </p>
              <p className="mt-2 text-sm text-yellow-200">Changes to these demo resolution statuses will be reverted.</p>
            </div>
            {resetMutation.isError && (
              <p role="alert" className="rounded border border-red-700 bg-red-950/50 p-3 text-sm text-red-200">
                Reset failed; no success was recorded. {resetMutation.error.message}
              </p>
            )}
            <div className="flex justify-end gap-3">
              <button
                type="button"
                autoFocus
                disabled={resetMutation.isPending}
                onClick={() => {
                  setResetDialogOpen(false);
                  resetMutation.reset();
                }}
                className="rounded border border-gray-600 px-4 py-2 text-sm text-gray-200 hover:bg-gray-700 disabled:opacity-50"
              >
                Cancel
              </button>
              <button
                type="button"
                disabled={resetMutation.isPending}
                onClick={() => resetMutation.mutate()}
                className="rounded bg-red-700 px-4 py-2 text-sm font-medium text-white hover:bg-red-600 disabled:opacity-50"
              >
                {resetMutation.isPending ? 'Resetting…' : 'Reset Demo Data'}
              </button>
            </div>
          </section>
        </div>
      )}

      {isLoading && (
        <div className="flex items-center justify-center py-8 text-gray-300" role="status" aria-label="Loading energy settings">
          <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-teal-400" />
          <span className="sr-only">Loading energy settings…</span>
        </div>
      )}

      {error && (
        <div className="rounded border border-red-700 bg-red-900/30 p-4 text-red-300" role="alert">
          Failed to load energy settings.
          <button className="ml-3 rounded bg-teal-600 px-2 py-0.5 text-sm hover:bg-teal-500" onClick={() => refetch()}>Retry</button>
        </div>
      )}

      {!isLoading && !error && configItems && configItems.length > 0 ? (
        <div className="rounded border border-gray-700 bg-gray-800 p-4 space-y-4">
          <div>
            <h3 className="text-lg font-medium text-teal-200">Energy Analysis Configuration</h3>
            <p className="text-sm text-gray-400">These parameters are saved to the application database and affect energy-analysis calculations.</p>
          </div>
          {configItems.map((item) => (
            <div key={item.key} className="space-y-1">
              <label className="block text-sm font-medium text-gray-300">
                {item.key.replace(/_/g, ' ')}
              </label>
              {item.description && (
                <p className="text-xs text-gray-500">{item.description}</p>
              )}
              <input
                type="text"
                className="w-full rounded border border-gray-600 bg-gray-900 px-3 py-2 text-sm text-gray-200 focus:border-teal-500 focus:outline-none"
                value={currentEdits[item.key] ?? item.value}
                onChange={(e) => setEdits({ ...currentEdits, [item.key]: e.target.value })}
              />
              {item.updated_at && (
                <p className="text-xs text-gray-600">Last updated: {new Date(item.updated_at).toLocaleString()}</p>
              )}
            </div>
          ))}

          <div className="flex items-center gap-3 pt-2">
            <button
              disabled={!hasChanges || saveStatus === 'saving'}
              onClick={() => saveMutation.mutate()}
              className="rounded bg-teal-600 px-4 py-2 text-sm font-medium text-white hover:bg-teal-500 disabled:opacity-50"
            >
              {saveStatus === 'saving' ? 'Saving…' : 'Save Changes'}
            </button>
            {hasChanges && (
              <button
                onClick={() => setEdits(null)}
                className="rounded border border-gray-600 px-4 py-2 text-sm text-gray-400 hover:bg-gray-700"
              >
                Discard
              </button>
            )}
            {saveStatus === 'saved' && <span className="text-sm text-green-400">✓ Saved</span>}
            {saveStatus === 'error' && <span className="text-sm text-red-400">Save failed. Check values.</span>}
          </div>
        </div>
      ) : !isLoading && !error ? (
        <p className="text-gray-400">No configuration keys found in database.</p>
      ) : null}
    </div>
  );
}
