import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
// Self-hosted fonts (bundled → served from 'self', so the framework's CSP
// `style-src/font-src 'self'` allows them; the remote Google Fonts @import was
// blocked by CSP). Linear/Vercel-minimal type system: a single Inter family
// across UI + display (tight negative tracking does the "display" work), with
// JetBrains Mono reserved for codes/data/numerals.
import '@fontsource/inter/400.css';
import '@fontsource/inter/500.css';
import '@fontsource/inter/600.css';
import '@fontsource/inter/700.css';
import '@fontsource/jetbrains-mono/400.css';
import '@fontsource/jetbrains-mono/500.css';
import './i18n';
import './store/useTheme'; // applies the persisted theme to <html> before first paint
import './index.css';
import { AuthProvider } from '@auth';
import { ProtectedRoute } from '@auth/login';
import App from './App';

const root = document.getElementById('root');
if (root) {
  createRoot(root).render(
    <StrictMode>
      <AuthProvider>
        <ProtectedRoute>
          <App />
        </ProtectedRoute>
      </AuthProvider>
    </StrictMode>
  );
}
