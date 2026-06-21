/**
 * Tenant switcher — visible only when the user belongs to more than one tenant.
 * Switching re-mints an access token scoped to the chosen tenant (membership
 * verified server-side), stores it, and reloads so the whole app re-renders
 * under the new tenant.
 */

import { useEffect, useState } from 'react';
import { Building2 } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { myTenants, switchTenant } from '../../api/tenants';
import type { MyTenant } from '../../types';

const TenantSwitcher = () => {
  const { t } = useTranslation();
  const [tenants, setTenants] = useState<MyTenant[]>([]);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    myTenants()
      .then(setTenants)
      .catch(() => setTenants([]));
  }, []);

  // Nothing to switch between → personal tenant or single-tenant: hide.
  if (tenants.length < 2) return null;

  const current = tenants.find((x) => x.is_default) || tenants[0];

  const onSwitch = async (tenantId: string) => {
    if (busy || tenantId === current.id) return;
    setBusy(true);
    try {
      const res = await switchTenant(tenantId);
      // Must match the key the auth context reads (client.ts getAccessToken).
      localStorage.setItem('auth_access_token', res.access_token);
      window.location.reload();
    } catch {
      setBusy(false);
    }
  };

  return (
    <div className="tenant-switcher" title={t('tenants.switcherTitle')}>
      <Building2 size={15} />
      <select
        value={current.id}
        disabled={busy}
        onChange={(e) => onSwitch(e.target.value)}
        aria-label={t('tenants.switcherTitle')}
      >
        {tenants.map((tn) => (
          <option key={tn.id} value={tn.id}>
            {tn.name}
          </option>
        ))}
      </select>
      <style>{`
        .tenant-switcher { display: inline-flex; align-items: center; gap: 0.35rem;
          color: var(--admin-text-muted); }
        .tenant-switcher select { background: transparent; color: var(--admin-text);
          border: 1px solid var(--admin-border, hsla(220,25%,40%,0.4)); border-radius: 0.4rem;
          padding: 0.25rem 0.5rem; font-size: 0.82rem; cursor: pointer; }
        .tenant-switcher select:disabled { opacity: 0.5; cursor: wait; }
      `}</style>
    </div>
  );
};

export default TenantSwitcher;
