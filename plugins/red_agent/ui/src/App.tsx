import { lazy, Suspense } from 'react';
import { Route, Routes } from 'react-router-dom';
import { Dashboard } from './routes/Dashboard';
import { ScansList } from './routes/ScansList';
import { ScanWizard } from './routes/ScanWizard';
import { ScanDetail } from './routes/ScanDetail';
import { Engagements } from './routes/Engagements';
import { EngagementDetail } from './routes/EngagementDetail';
import { FindingsExplorer } from './routes/FindingsExplorer';
import { ScopePolicy } from './routes/ScopePolicy';
import { TargetsList } from './routes/TargetsList';
import { TargetDetail } from './routes/TargetDetail';
import { NewTarget } from './routes/NewTarget';
import { Approvals } from './routes/Approvals';
import { BinaryScan } from './routes/BinaryScan';
import { FleetList } from './routes/FleetList';
import { Sidebar } from './components/shell/Sidebar';
import { Topbar } from './components/shell/Topbar';

const AttackSurface = lazy(() =>
  import('./routes/AttackSurface').then((m) => ({ default: m.AttackSurface }))
);

export function App() {
  return (
    <div className="grid h-full grid-cols-1 grid-rows-1 lg:grid-cols-[260px_1fr]">
      <Sidebar />
      <div className="flex h-full min-w-0 flex-col">
        <Topbar />
        <main className="flex-1 overflow-auto">
          <div className="mx-auto max-w-[1680px] px-4 py-5 sm:px-6 lg:px-8">
            <Routes>
              <Route path="/" element={<Dashboard />} />
              <Route path="/targets" element={<TargetsList />} />
              <Route path="/engagements" element={<Engagements />} />
              <Route path="/engagements/:id" element={<EngagementDetail />} />
              <Route path="/targets/new" element={<NewTarget />} />
              <Route path="/targets/:id" element={<TargetDetail />} />
              <Route path="/scans" element={<ScansList />} />
              <Route path="/scans/new" element={<ScanWizard />} />
              <Route path="/scans/:id" element={<ScanDetail />} />
              <Route path="/binary-analysis" element={<BinaryScan />} />
              <Route path="/findings" element={<FindingsExplorer />} />
              <Route path="/approvals" element={<Approvals />} />
              <Route path="/fleet" element={<FleetList />} />
              <Route
                path="/graph"
                element={
                  <div className="h-[calc(100vh-7rem)]">
                    <Suspense fallback={<RouteFallback label="loading graph engine…" />}>
                      <AttackSurface />
                    </Suspense>
                  </div>
                }
              />
              <Route path="/settings/scope" element={<ScopePolicy />} />
            </Routes>
          </div>
        </main>
      </div>
    </div>
  );
}

function RouteFallback({ label }: { label: string }) {
  return (
    <div className="grid h-full place-items-center">
      <div className="flex items-center gap-2 font-mono text-sm text-brand">
        <span className="h-2 w-2 rounded-full bg-brand animate-pulse" />
        {label}
      </div>
    </div>
  );
}
