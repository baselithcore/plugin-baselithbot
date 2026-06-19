/**
 * Impersonation banner — control-plane host shell.
 *
 * When an administrator is acting as another user (an impersonation token held
 * by the shared `@auth` context), this persistent, high-visibility bar sits
 * above the topbar so the impersonated state is unmistakable — a core safety
 * requirement for "log in as user". It offers a one-click Stop that restores
 * the administrator and returns them to the auth console.
 *
 * Self-contained on purpose: it consumes only the dependency-free `useAuth()`
 * from the `@auth` barrel (the login UI's `ImpersonationBanner` pulls
 * react-i18next via the auth catalog and cannot ship through that lean barrel),
 * and renders with this plugin's own i18n + lucide.
 */
import { useState } from 'react';
import { UserCog, LogOut } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { useAuth } from '@auth';

export function ImpersonationBanner() {
  const { t } = useTranslation();
  const { isImpersonating, impersonator, user, stopImpersonation } = useAuth();
  const [stopping, setStopping] = useState(false);

  if (!isImpersonating) return null;

  const target = user?.email ?? user?.username ?? user?.id ?? '';
  const admin = impersonator?.email ?? impersonator?.id ?? '';

  const handleStop = async () => {
    setStopping(true);
    try {
      await stopImpersonation();
      // Administrator restored — return to the auth console they came from.
      window.location.href = '/auth/';
    } catch {
      setStopping(false);
    }
  };

  return (
    <div
      role="alert"
      className="flex shrink-0 flex-wrap items-center justify-center gap-3 bg-amber-600 px-4 py-2 text-sm font-semibold text-white shadow-md"
    >
      <span className="inline-flex items-center gap-2">
        <UserCog size={18} aria-hidden />
        {t('impersonation.banner', { target, admin })}
      </span>
      <button
        type="button"
        onClick={handleStop}
        disabled={stopping}
        className="inline-flex items-center gap-1.5 rounded-md bg-white px-3 py-1 text-xs font-semibold text-amber-700 transition hover:opacity-85 disabled:cursor-default disabled:opacity-60"
      >
        <LogOut size={15} aria-hidden />
        {stopping ? t('impersonation.stopping') : t('impersonation.stop')}
      </button>
    </div>
  );
}
