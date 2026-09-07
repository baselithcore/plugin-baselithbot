import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AuthProvider } from '@baselith/auth';
import { ProtectedRoute } from '@baselith/auth/login';
// Library build extracts CSS instead of injecting it.
import '@baselith/auth/style.css';
import App from './App';
import { DashboardProvider } from './components/DashboardProvider';
import { ErrorBoundary } from './components/ErrorBoundary';
import './styles/index.css';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      staleTime: 5_000,
      retry: 1,
    },
  },
});

const rootEl = document.getElementById('root')!;

ReactDOM.createRoot(rootEl).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <ProtectedRoute>
          <ErrorBoundary>
            <DashboardProvider>
              <BrowserRouter basename={import.meta.env.BASE_URL.replace(/\/$/, '')}>
                <App />
              </BrowserRouter>
            </DashboardProvider>
          </ErrorBoundary>
        </ProtectedRoute>
      </AuthProvider>
    </QueryClientProvider>
  </React.StrictMode>
);
