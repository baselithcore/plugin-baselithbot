import React from 'react';
import ReactDOM from 'react-dom/client';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MotionConfig } from 'framer-motion';
import { App } from './App.js';
import { AuthGate } from './components/AuthGate.js';
import { initObservability } from './lib/observability.js';
import './styles/globals.css';

initObservability();

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60_000,
      gcTime: 30 * 60_000,
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});

// Hidden hello for the curious
if (typeof window !== 'undefined') {
  const hi = '%cdbview · schema intelligence';
  const sub = '%c⌘K to navigate · ⌘[ / ⌘] toggle panels · ↵ to query';
  const head =
    'background:linear-gradient(90deg,#2dd4bf,#60a5fa);color:#04161a;padding:6px 10px;border-radius:6px;font-weight:600;letter-spacing:0.02em';
  const body =
    'color:#a1a1aa;font:11px/1.4 ui-monospace,SFMono-Regular,Menlo,monospace;padding:6px 0';
  // eslint-disable-next-line no-console
  console.log(`${hi}\n${sub}`, head, body);
}

ReactDOM.createRoot(document.getElementById('root') as HTMLElement).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <MotionConfig reducedMotion="user" transition={{ duration: 0.22, ease: [0.22, 1, 0.36, 1] }}>
        <AuthGate>
          <App />
        </AuthGate>
      </MotionConfig>
    </QueryClientProvider>
  </React.StrictMode>,
);
