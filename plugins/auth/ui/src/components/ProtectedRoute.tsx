/**
 * Protected Route Component
 *
 * Wrapper that requires authentication to access children.
 */

import { type ReactNode } from 'react';
import { ShieldAlert } from 'lucide-react';
import { useAuthT } from '../i18n/standalone';
import { useAuth } from '../hooks/useAuthContext';
import LoginPage from './LoginPage';

interface ProtectedRouteProps {
  children: ReactNode;
  requiredRole?: string;
  requiredTab?: string;
}

export function ProtectedRoute({ children, requiredRole, requiredTab }: ProtectedRouteProps) {
  const t = useAuthT();
  const { isAuthenticated, isLoading, hasRole, canAccessTab, user } = useAuth();

  if (isLoading) {
    return (
      <div className="auth-loading">
        <div className="auth-spinner-large" />
        <p>{t('protected.loading')}</p>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <LoginPage />;
  }

  if (requiredRole && !hasRole(requiredRole)) {
    return (
      <div className="auth-forbidden">
        <ShieldAlert size={64} className="auth-forbidden-icon" />
        <h1>{t('protected.accessDenied')}</h1>
        <p>{t('protected.noPagePermission')}</p>
        <p className="auth-forbidden-detail">
          {t('protected.requiredRole')} <code>{requiredRole}</code>
        </p>
      </div>
    );
  }

  if (requiredTab && !canAccessTab(requiredTab)) {
    return (
      <div className="auth-forbidden">
        <ShieldAlert size={64} className="auth-forbidden-icon" />
        <h1>{t('protected.accessDenied')}</h1>
        <p>{t('protected.noSectionAccess')}</p>
        {user?.allowed_tabs && (
          <p className="auth-forbidden-detail">
            {t('protected.limitedTo', { tabs: user.allowed_tabs.join(', ') })}
          </p>
        )}
      </div>
    );
  }

  return <>{children}</>;
}

/**
 * Hook for conditional rendering based on auth.
 */
export function useProtectedContent(requiredRole?: string, requiredTab?: string) {
  const { isAuthenticated, hasRole, canAccessTab } = useAuth();

  const isAllowed =
    isAuthenticated &&
    (!requiredRole || hasRole(requiredRole)) &&
    (!requiredTab || canAccessTab(requiredTab));

  return { isAllowed };
}
