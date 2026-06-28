/**
 * Always-on LLM budget overlay.
 *
 * A fixed banner pinned to the top of the auth shells that polls the signed-in
 * user's month-to-date LLM spend and stays visible whenever they cross the warn
 * threshold (amber, ≥80%) or hit the cap (red, 100% — AI requests are blocked
 * server-side). Hidden while under threshold or uncapped. Non-dismissible by
 * design so the state is always in view; it never covers navigation, so an admin
 * can still reach the Budget tab to raise the cap or reset usage.
 */

import { useEffect, useState } from 'react';
import { AlertTriangle, Ban } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { getMyLlmUsage, type MyLlmUsage } from '../../api/account';
import { getAccessToken } from '../../api/client';

const POLL_MS = 30000;

export default function UsageOverlay() {
  const { t } = useTranslation();
  const [usage, setUsage] = useState<MyLlmUsage | null>(null);

  useEffect(() => {
    let alive = true;
    const load = () => {
      const token = getAccessToken();
      if (!token) return;
      getMyLlmUsage(token)
        .then((u) => alive && setUsage(u))
        .catch(() => {});
    };
    load();
    const id = setInterval(load, POLL_MS);
    const onVisible = () => document.visibilityState === 'visible' && load();
    document.addEventListener('visibilitychange', onVisible);
    return () => {
      alive = false;
      clearInterval(id);
      document.removeEventListener('visibilitychange', onVisible);
    };
  }, []);

  // Nothing to show: not loaded, uncapped, or comfortably under the threshold.
  if (!usage || usage.cap_usd == null || usage.status === 'ok') return null;

  const blocked = usage.status === 'blocked';
  const pct = usage.percent_used ?? 0;

  return (
    <div
      role="alert"
      aria-live="assertive"
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        zIndex: 10000,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        gap: 10,
        padding: '10px 16px',
        fontSize: 14,
        fontWeight: 600,
        color: '#fff',
        background: blocked ? '#be123c' : '#b45309',
        boxShadow: '0 2px 10px rgba(0,0,0,.25)',
      }}
    >
      {blocked ? <Ban size={18} /> : <AlertTriangle size={18} />}
      <span>
        {blocked ? t('overlay.blocked', { period: usage.period }) : t('overlay.warning', { pct })}
      </span>
    </div>
  );
}
