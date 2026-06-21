import { MotionConfig } from 'framer-motion';
import React from 'react';
import ReactDOM from 'react-dom/client';
import { AuthProvider as CoreAuthProvider } from '@auth';
import { ProtectedRoute } from '@auth/login';
import { App } from './App';
import { ErrorBoundary } from './components/ErrorBoundary';
import { initTheme } from './components/ThemeToggle';
import { AuthProvider } from './contexts/AuthContext';
import { BrandingProvider } from './contexts/BrandingContext';
import { DomainProvider } from './contexts/DomainContext';
import { initObservability } from './lib/observability';
// i18n bootstrap (en + it) — side-effect init before first render.
import './i18n';
// House-style typography (self-hosted variable fonts — no external request,
// coherent with the "i dati restano sul tuo computer" privacy ethos).
// Display = Bricolage Grotesque (characterful editorial grotesque),
// body/UI = Hanken Grotesk, code = JetBrains Mono. Imported before
// index.css so the @font-face rules register before the @theme tokens
// reference them. Tenant branding overrides colours at runtime, not type —
// the typeface trio is the fixed Grafiphy house signature.
import '@fontsource-variable/bricolage-grotesque/index.css';
import '@fontsource-variable/hanken-grotesk/index.css';
import '@fontsource-variable/jetbrains-mono/index.css';
import './index.css';

initTheme();
// RUM opt-in: senza VITE_OTLP_ENDPOINT + faro packages → no-op.
void initObservability();

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <ErrorBoundary>
      {/* Central auth owns identity: AuthProvider supplies the session and
          ProtectedRoute renders the shared login wall until authenticated.
          Everything below only ever runs for a logged-in user. */}
      <CoreAuthProvider>
        <ProtectedRoute>
          <BrandingProvider>
            <DomainProvider>
              {/* Wiki AuthProvider = thin adapter over @auth (perms map). */}
              <AuthProvider>
                {/* reducedMotion="user" respects prefers-reduced-motion */}
                <MotionConfig reducedMotion="user">
                  <App />
                </MotionConfig>
              </AuthProvider>
            </DomainProvider>
          </BrandingProvider>
        </ProtectedRoute>
      </CoreAuthProvider>
    </ErrorBoundary>
  </React.StrictMode>
);
