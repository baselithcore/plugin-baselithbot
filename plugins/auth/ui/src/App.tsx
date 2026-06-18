import { useEffect, useState } from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import AdminPanel from './components/AdminPanel';
import { AuthProvider, useAuth } from './index';
import { ProtectedRoute, LoginPage } from './login';
import ForgotPasswordPage from './components/public/ForgotPasswordPage';
import ResetPasswordPage from './components/public/ResetPasswordPage';
import VerifyEmailPage from './components/public/VerifyEmailPage';
import AcceptInvitePage from './components/public/AcceptInvitePage';
import AccountPage from './components/account/AccountPage';
import ImpersonationBanner from './components/ImpersonationBanner';
import SetupWizard from './components/public/SetupWizard';
import { getSetupStatus } from './api/setup';

/**
 * Reads an optional `?redirect=` target from the current URL. Only same-origin
 * relative paths ('/...') are honored, so a logged-out plugin (e.g.
 * baselithcontrol) can send the user here to re-authenticate and bounce back,
 * while open-redirect to external origins is rejected.
 */
const getRedirect = (): string | null => {
  const redirect = new URLSearchParams(window.location.search).get('redirect');
  if (redirect && redirect.startsWith('/') && !redirect.startsWith('//')) {
    return redirect;
  }
  return null;
};

const LoginWrapper = () => {
  const handleLoginSuccess = () => {
    window.location.href = getRedirect() || '/auth/';
  };

  return <LoginPage onSuccess={handleLoginSuccess} />;
};

/**
 * Root route. The auth SPA is reached both as its own admin console and as the
 * central login (other plugins redirect here on logout). Once authenticated, if
 * the caller passed a `?redirect=` target we bounce back there instead of
 * rendering the admin panel — and we do this BEFORE the admin-role gate so a
 * non-admin plugin user still returns to their plugin rather than hitting an
 * access-denied screen.
 */
const RootRoute = () => {
  const { isAuthenticated, isLoading, hasRole } = useAuth();
  const redirect = getRedirect();

  if (!isLoading && isAuthenticated && redirect) {
    window.location.replace(redirect);
    return null;
  }

  // Non-admin users get the self-service account surface instead of an
  // access-denied wall; admins get the management console.
  if (!isLoading && isAuthenticated && !hasRole('admin')) {
    window.location.replace('/auth/account');
    return null;
  }

  return (
    <ProtectedRoute requiredRole="admin">
      <AdminPanel />
    </ProtectedRoute>
  );
};

/**
 * Gates the whole app behind first-run setup. On a fresh install (empty user
 * table) the setup wizard is shown instead of the login/app; once any account
 * exists the check is a cheap GET that returns `needs_setup: false` and the
 * normal routes render. Fails open (renders the app) if the probe errors, so a
 * transient backend hiccup never blocks login.
 */
const SetupGate = ({ children }: { children: React.ReactNode }) => {
  const [state, setState] = useState<'checking' | 'needed' | 'ready'>('checking');

  useEffect(() => {
    let cancelled = false;
    getSetupStatus()
      .then((s) => !cancelled && setState(s.needs_setup ? 'needed' : 'ready'))
      .catch(() => !cancelled && setState('ready'));
    return () => {
      cancelled = true;
    };
  }, []);

  if (state === 'checking') {
    return <div className="auth-page" aria-busy="true" />;
  }
  if (state === 'needed') {
    return <SetupWizard onComplete={() => (window.location.href = '/auth/')} />;
  }
  return <>{children}</>;
};

const App = () => {
  return (
    <AuthProvider>
      <SetupGate>
        <Router basename="/auth">
          <ImpersonationBanner />
          <Routes>
            <Route path="/login" element={<LoginWrapper />} />
            <Route path="/forgot-password" element={<ForgotPasswordPage />} />
            <Route path="/reset-password" element={<ResetPasswordPage />} />
            <Route path="/verify-email" element={<VerifyEmailPage />} />
            <Route path="/accept-invite" element={<AcceptInvitePage />} />
            <Route
              path="/account"
              element={
                <ProtectedRoute>
                  <AccountPage />
                </ProtectedRoute>
              }
            />
            <Route path="/" element={<RootRoute />} />
          </Routes>
        </Router>
      </SetupGate>
    </AuthProvider>
  );
};

export default App;
