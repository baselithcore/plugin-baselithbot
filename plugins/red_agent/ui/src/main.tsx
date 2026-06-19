import React from 'react';
import ReactDOM from 'react-dom/client';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter } from 'react-router-dom';
import { AuthProvider } from '@auth';
import { ProtectedRoute } from '@auth/login';
import { App } from './App';
import './theme/global.css';

const qc = new QueryClient({
  defaultOptions: { queries: { retry: 1, staleTime: 30_000 } },
});

// Operator console signature — for the curious dev who opens devtools.
if (typeof window !== 'undefined') {
  // eslint-disable-next-line no-console
  console.log(
    '%c// red_agent %c— operator console. authorized targets only.',
    'color:#5b9bd5;font-family:JetBrains Mono,monospace;font-weight:600',
    'color:#727a8c;font-family:JetBrains Mono,monospace'
  );
}

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <QueryClientProvider client={qc}>
      <AuthProvider>
        <ProtectedRoute>
          <BrowserRouter basename="/red-agent/ui">
            <App />
          </BrowserRouter>
        </ProtectedRoute>
      </AuthProvider>
    </QueryClientProvider>
  </React.StrictMode>
);
