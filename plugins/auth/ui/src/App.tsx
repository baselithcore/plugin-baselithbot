import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import AdminPanel from './components/AdminPanel';
import { AuthProvider, useAuth } from './index';
import { ProtectedRoute, LoginPage } from './login';
import ForgotPasswordPage from './components/public/ForgotPasswordPage';
import ResetPasswordPage from './components/public/ResetPasswordPage';
import VerifyEmailPage from './components/public/VerifyEmailPage';
import AcceptInvitePage from './components/public/AcceptInvitePage';
import AccountPage from './components/account/AccountPage';

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

const App = () => {
  return (
    <AuthProvider>
      <Router basename="/auth">
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
    </AuthProvider>
  );
};

export default App;
