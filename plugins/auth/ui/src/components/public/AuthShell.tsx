/**
 * Shared chrome for the public auth pages (forgot/reset/verify/invite).
 * Mirrors the login card styling so the flow feels cohesive.
 */

import type { ReactNode } from 'react';
import AuthLogo from '../ui/AuthLogo';
import LanguageSwitcher from '../ui/LanguageSwitcher';

interface AuthShellProps {
  title: string;
  subtitle?: string;
  children: ReactNode;
}

export default function AuthShell({ title, subtitle, children }: AuthShellProps) {
  return (
    <div className="auth-page">
      <div className="aurora" aria-hidden="true" />
      <div className="auth-lang-floating">
        <LanguageSwitcher />
      </div>
      <div className="auth-card">
        <div className="auth-header">
          <div className="auth-logo">
            <AuthLogo size={64} />
          </div>
          <h1 className="auth-title">{title}</h1>
          {subtitle && <p className="auth-subtitle">{subtitle}</p>}
        </div>
        {children}
      </div>
    </div>
  );
}
