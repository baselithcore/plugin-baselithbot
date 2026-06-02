import { MotionConfig } from 'framer-motion';
import React from 'react';
import ReactDOM from 'react-dom/client';
import { App } from './App';
import { ErrorBoundary } from './components/ErrorBoundary';
import { initTheme } from './components/ThemeToggle';
import { AuthProvider } from './contexts/AuthContext';
import { BrandingProvider } from './contexts/BrandingContext';
import { DomainProvider } from './contexts/DomainContext';
import { initObservability } from './lib/observability';
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
      <BrandingProvider>
        <DomainProvider>
          {/* AuthProvider in cima ai consumer (App, useConversations) ma
              sotto Branding/Domain perché AuthPage usa useDomain per
              il logo + label brand. */}
          <AuthProvider>
            {/* reducedMotion="user" respects the system prefers-reduced-motion setting */}
            <MotionConfig reducedMotion="user">
              <App />
            </MotionConfig>
          </AuthProvider>
        </DomainProvider>
      </BrandingProvider>
    </ErrorBoundary>
  </React.StrictMode>
);
