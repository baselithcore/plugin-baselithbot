import { useEffect, useState } from 'react';
import { Building2 } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { fetchMyTenants, switchTenant } from '@/lib/api';
import type { MyTenant } from '@/types';

/**
 * App-wide tenant switcher. Visible only when the signed-in user belongs to
 * more than one tenant. Switching mints a fresh access token scoped to the
 * chosen tenant (membership verified server-side), stores it under the shared
 * `auth_access_token` key, and reloads so the whole shell re-renders.
 */
export function TenantSwitcher() {
  const { t } = useTranslation();
  const [tenants, setTenants] = useState<MyTenant[]>([]);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    fetchMyTenants()
      .then(setTenants)
      .catch(() => setTenants([]));
  }, []);

  // Personal tenant or single membership → nothing to switch between.
  if (tenants.length < 2) return null;

  const current = tenants.find((x) => x.is_default) ?? tenants[0];

  const onChange = async (id: string) => {
    if (busy || id === current.id) return;
    setBusy(true);
    try {
      const token = await switchTenant(id);
      localStorage.setItem('auth_access_token', token);
      window.location.reload();
    } catch {
      setBusy(false);
    }
  };

  return (
    <div
      className="hidden items-center gap-1.5 rounded-lg border brd bg-[var(--surface-inset)] px-2 py-1.5 md:inline-flex"
      title={t('tenant.switch')}
    >
      <Building2 className="h-3.5 w-3.5 t-dim" />
      <select
        value={current.id}
        disabled={busy}
        onChange={(e) => onChange(e.target.value)}
        aria-label={t('tenant.switch')}
        className="bg-transparent text-[12px] font-semibold t-primary outline-none disabled:opacity-50"
      >
        {tenants.map((tn) => (
          <option key={tn.id} value={tn.id}>
            {tn.name}
          </option>
        ))}
      </select>
    </div>
  );
}
