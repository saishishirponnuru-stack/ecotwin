import { lazy, Suspense } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import Sidebar from './components/layout/Sidebar';
import Header from './components/layout/Header';
import { ThemeProvider } from './theme/ThemeProvider';

const OverviewPage = lazy(() => import('./features/overview/OverviewPage'));
const MachineFleetPage = lazy(() => import('./features/machine/MachineFleetPage'));
const MachineDetailPage = lazy(() => import('./features/machine/MachineDetailPage'));
const RecommendationsPage = lazy(() => import('./features/recommendation/RecommendationsPage'));
const AnomalyCenterPage = lazy(() => import('./features/anomaly/AnomalyCenterPage'));
const WhatIfLabPage = lazy(() => import('./features/whatif/WhatIfLabPage'));
const ImpactVerificationPage = lazy(() => import('./features/impact/ImpactVerificationPage'));
const EnergyIntelligencePage = lazy(() => import('./features/energy/EnergyIntelligencePage'));
const DataManagementPage = lazy(() => import('./features/data/DataManagementPage'));
const ReportsPage = lazy(() => import('./features/reports/ReportsPage'));
const SettingsPage = lazy(() => import('./features/settings/SettingsPage'));

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 2,
      refetchOnWindowFocus: false,
    },
  },
});

function App() {
  return (
    <ThemeProvider>
      <BrowserRouter>
        <QueryClientProvider client={queryClient}>
          <div className="app-shell flex h-screen bg-gray-900 text-gray-100">
            <Sidebar />
            <div className="flex flex-col flex-1 overflow-hidden">
              <Header title="EcoTwin — Smart Manufacturing Energy Intelligence" />
              <main className="flex-1 overflow-auto p-6">
                <Suspense fallback={<div className="flex h-40 items-center justify-center text-sm text-gray-400">Loading workspace…</div>}>
                  <Routes>
                    <Route path="/" element={<OverviewPage />} />
                    <Route path="/machine" element={<MachineFleetPage />} />
                    <Route path="/machine/:machineId" element={<MachineDetailPage />} />
                    <Route path="/energy" element={<EnergyIntelligencePage />} />
                    <Route path="/anomaly" element={<AnomalyCenterPage />} />
                    <Route path="/recommendations" element={<RecommendationsPage />} />
                    <Route path="/whatif" element={<WhatIfLabPage />} />
                    <Route path="/impact" element={<ImpactVerificationPage />} />
                    <Route path="/data" element={<DataManagementPage />} />
                    <Route path="/reports" element={<ReportsPage />} />
                    <Route path="/settings" element={<SettingsPage />} />
                    <Route path="*" element={<Navigate to="/" replace />} />
                  </Routes>
                </Suspense>
              </main>
            </div>
          </div>
        </QueryClientProvider>
      </BrowserRouter>
    </ThemeProvider>
  );
}

export default App;
