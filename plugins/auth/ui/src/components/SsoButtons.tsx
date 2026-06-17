/**
 * SSO login buttons on the login wall. Fetches enabled identity providers and
 * renders one "Continue with …" button each; clicking starts the SP-initiated
 * flow at the backend. Renders nothing when no providers are configured.
 */

import { useEffect, useState } from 'react';
import { useAuthT } from '../i18n/standalone';

interface Provider {
  slug: string;
  name: string;
  protocol: string;
}

export default function SsoButtons() {
  const t = useAuthT();
  const [providers, setProviders] = useState<Provider[]>([]);

  useEffect(() => {
    fetch('/api/auth/sso/providers', { credentials: 'include' })
      .then((r) => (r.ok ? r.json() : []))
      .then((list) => Array.isArray(list) && setProviders(list))
      .catch(() => setProviders([]));
  }, []);

  if (providers.length === 0) return null;

  return (
    <div className="auth-sso">
      <div className="auth-divider">
        <span>{t('login.or')}</span>
      </div>
      {providers.map((p) => (
        <a
          key={p.slug}
          className="auth-button auth-button-secondary"
          href={`/api/auth/sso/${p.slug}/login`}
        >
          {t('login.ssoContinue', { name: p.name })}
        </a>
      ))}
    </div>
  );
}
