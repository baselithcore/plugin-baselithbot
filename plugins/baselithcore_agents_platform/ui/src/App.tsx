import { lazy, Suspense, type ReactNode } from 'react';
import { Navigate, Route, Routes } from 'react-router-dom';
import { AuthProvider, useAuth } from '@auth';
import { ProtectedRoute } from '@auth/login';
import { Layout } from './components/Layout';
import { Skeleton } from './components/Skeleton';
import { NAV, PLUGIN } from './nav';

const Builder = lazy(() => import('./pages/Builder').then((m) => ({ default: m.Builder })));
const Agents = lazy(() => import('./pages/Agents').then((m) => ({ default: m.Agents })));
const Runs = lazy(() => import('./pages/Runs').then((m) => ({ default: m.Runs })));
const Schedules = lazy(() => import('./pages/Schedules').then((m) => ({ default: m.Schedules })));
const Docs = lazy(() => import('./pages/Docs').then((m) => ({ default: m.Docs })));
const Models = lazy(() => import('./pages/Models').then((m) => ({ default: m.Models })));
const NotFound = lazy(() => import('./pages/NotFound').then((m) => ({ default: m.NotFound })));

function PageFallback() {
  return (
    <div className="grid gap-4" aria-busy="true">
      <Skeleton height={120} />
      <Skeleton height={220} />
    </div>
  );
}

function AccessDenied() {
  return (
    <div className="grid min-h-screen place-items-center px-4 text-center">
      <div className="glass max-w-md rounded-2xl p-8 shadow-glass">
        <h1 className="text-lg font-semibold text-slate-100">Access denied</h1>
        <p className="mt-2 text-sm text-slate-400">
          Your account is not authorized to view the Agents Platform.
        </p>
      </div>
    </div>
  );
}

/** Per-section RBAC gate. Redirects to the first allowed section when denied;
 *  shows AccessDenied only when every section is restricted for this caller. */
function Guard({ id, children }: { id: string; children: ReactNode }) {
  const { canAccessTab } = useAuth();
  if (canAccessTab(id, PLUGIN)) return <>{children}</>;
  const firstAllowed = NAV.find((n) => canAccessTab(n.id, PLUGIN));
  if (!firstAllowed) return <AccessDenied />;
  return <Navigate to={firstAllowed.to} replace />;
}

function Dashboard() {
  return (
    <Layout>
      <Suspense fallback={<PageFallback />}>
        <Routes>
          <Route
            path="/"
            element={
              <Guard id="builder">
                <Builder />
              </Guard>
            }
          />
          <Route
            path="/agents"
            element={
              <Guard id="agents">
                <Agents />
              </Guard>
            }
          />
          <Route
            path="/runs"
            element={
              <Guard id="runs">
                <Runs />
              </Guard>
            }
          />
          <Route
            path="/schedules"
            element={
              <Guard id="schedules">
                <Schedules />
              </Guard>
            }
          />
          <Route
            path="/docs"
            element={
              <Guard id="docs">
                <Docs />
              </Guard>
            }
          />
          <Route
            path="/models"
            element={
              <Guard id="models">
                <Models />
              </Guard>
            }
          />
          <Route path="*" element={<NotFound />} />
        </Routes>
      </Suspense>
    </Layout>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <ProtectedRoute>
        <Dashboard />
      </ProtectedRoute>
    </AuthProvider>
  );
}
