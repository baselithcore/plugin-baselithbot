import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { setPluginConfig } from '@/lib/api';
import { useUiStore } from '@/store/useUiStore';
import { useControlStore } from '@/store/useControlStore';

interface Props {
  plugin: string;
  enabled: boolean | null;
  canControl: boolean;
}

// Persists the plugin's `enabled` flag in configs/plugins.yaml (admin-gated,
// audited server-side). A config-level switch — distinct from the runtime
// enable/disable buttons — and durable across restarts.
export function ConfigToggle({ plugin, enabled, canControl }: Props) {
  const { t } = useTranslation();
  const ask = useUiStore((s) => s.ask);
  const pushToast = useUiStore((s) => s.pushToast);
  const patchPlugin = useControlStore((s) => s.patchPlugin);
  const [on, setOn] = useState(enabled !== false); // null (absent) → enabled
  const [busy, setBusy] = useState(false);

  const toggle = async () => {
    const next = !on;
    const key = next ? 'config.confirm_enable' : 'config.confirm_disable';
    if (!(await ask(t(key, { plugin })))) return;
    setBusy(true);
    try {
      const res = await setPluginConfig(plugin, next);
      if (res.ok) {
        setOn(next);
        // Reflect the new lifecycle state on the card immediately (realtime),
        // independent of the SSE feed.
        patchPlugin(plugin, { state: res.state, config_enabled: next });
        pushToast(t('config.saved', { plugin }), 'success');
      } else {
        pushToast(t('config.failed', { plugin, message: res.message }), 'danger');
      }
    } catch (err) {
      pushToast(t('config.failed', { plugin, message: String(err) }), 'danger');
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="glass space-y-3 p-5">
      <h3 className="text-[11px] font-semibold uppercase tracking-wider t-faint">
        {t('config.title')}
      </h3>
      <div className="flex items-center justify-between gap-3">
        <div className="min-w-0">
          <div className="text-[13px] font-semibold t-primary">{t('config.enabled_label')}</div>
          <p className="mt-0.5 text-[11px] leading-relaxed t-dim">{t('config.hint')}</p>
        </div>
        <button
          type="button"
          role="switch"
          aria-checked={on}
          aria-label={t('config.enabled_label')}
          disabled={!canControl || busy}
          onClick={toggle}
          className={`relative h-6 w-11 shrink-0 rounded-full transition duration-200 disabled:cursor-not-allowed disabled:opacity-40 ${
            on ? 'bg-emerald-500' : 'bg-[var(--border-strong)]'
          }`}
        >
          <span
            className={`absolute top-0.5 h-5 w-5 rounded-full bg-white shadow transition-all duration-200 ${
              on ? 'left-[22px]' : 'left-0.5'
            }`}
          />
        </button>
      </div>
      {!canControl && <p className="text-[11px] t-faint">{t('rbac.read_only')}</p>}
    </div>
  );
}
