import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { ArrowLeft, ExternalLink, Layers, PlayCircle, Power, RefreshCw } from 'lucide-react';
import type { LifecycleOp, PluginCard } from '@/types';
import { runAction, setPluginConfig } from '@/lib/api';
import { useUiStore } from '@/store/useUiStore';
import { useControlStore } from '@/store/useControlStore';
import { HealthBadge } from '@/components/widgets/HealthBadge';

interface Props {
  card: PluginCard;
  launchUrl: string | null;
  canControl: boolean;
  healthTip?: string;
  onBack: () => void;
}

const OPS: { op: LifecycleOp; icon: typeof Power; cls: string }[] = [
  { op: 'enable', icon: PlayCircle, cls: 'hover:border-emerald-500/50 hover:text-emerald-500' },
  {
    op: 'reload',
    icon: RefreshCw,
    cls: 'hover:border-[var(--accent-border)] hover:text-[var(--accent)]',
  },
  { op: 'disable', icon: Power, cls: 'hover:border-rose-500/50 hover:text-rose-500' },
];

// Sticky identity + command bar: breadcrumb, plugin identity, live health, and
// the primary actions (launch the standalone UI + lifecycle controls). The
// detail view previously had no lifecycle actions at all — only a buried config
// toggle — so surfacing enable/reload/disable here is the functional upgrade.
export function Header({ card, launchUrl, canControl, healthTip, onBack }: Props) {
  const { t } = useTranslation();
  const ask = useUiStore((s) => s.ask);
  const pushToast = useUiStore((s) => s.pushToast);
  const patchPlugin = useControlStore((s) => s.patchPlugin);
  const [busy, setBusy] = useState<LifecycleOp | null>(null);

  const act = async (op: LifecycleOp) => {
    if (!(await ask(t('action.confirm', { op, plugin: card.name })))) return;
    setBusy(op);
    try {
      const res =
        op === 'reload'
          ? await runAction(card.name, 'reload')
          : await setPluginConfig(card.name, op === 'enable');
      if (res.ok) {
        patchPlugin(card.name, {
          state: res.state,
          ...(op !== 'reload' ? { config_enabled: op === 'enable' } : {}),
        });
        pushToast(t('action.ok', { op }), 'success');
      } else {
        pushToast(t('action.failed', { op, message: res.message }), 'danger');
      }
    } catch (err) {
      pushToast(t('action.failed', { op, message: String(err) }), 'danger');
    } finally {
      setBusy(null);
    }
  };

  const disabledFor = (op: LifecycleOp) =>
    busy !== null ||
    (op === 'enable' && card.state === 'active') ||
    (op === 'disable' && card.state === 'disabled') ||
    (op === 'reload' && card.state !== 'active');

  return (
    <div className="sticky top-0 z-10 -mx-1 flex flex-col gap-4 border-b brd bg-[var(--bg)]/85 px-1 pb-4 pt-1 backdrop-blur">
      <button
        type="button"
        onClick={onBack}
        className="flex w-fit items-center gap-1.5 text-[12px] font-medium t-dim transition hover:text-[var(--text)]"
      >
        <ArrowLeft className="h-3.5 w-3.5" />
        {t('detail.back')}
      </button>

      <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
        <div className="flex min-w-0 items-center gap-3">
          <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-lg bg-[var(--accent-soft)] accent-ring t-accent">
            <Layers className="h-5 w-5" />
          </span>
          <div className="min-w-0">
            <div className="flex items-center gap-2.5">
              <h1 className="font-display truncate text-[1.45rem] font-bold tracking-tight t-primary">
                {card.name}
              </h1>
              <HealthBadge state={card.state} title={healthTip} />
            </div>
            <p className="text-[12px] font-medium tabular-nums t-dim">
              {t('card.version', { version: card.version })}
            </p>
          </div>
        </div>

        <div className="flex shrink-0 flex-wrap items-center gap-1.5">
          {canControl &&
            OPS.map(({ op, icon: Icon, cls }) => (
              <button
                key={op}
                type="button"
                disabled={disabledFor(op)}
                onClick={() => act(op)}
                title={
                  disabledFor(op) && busy === null ? t(`action.${op}_disabled`) : t(`action.${op}`)
                }
                className={`inline-flex items-center gap-1.5 rounded-lg border brd px-2.5 py-1.5 text-[12px] font-medium t-dim transition disabled:cursor-not-allowed disabled:opacity-40 disabled:hover:border-[var(--border)] ${cls}`}
              >
                <Icon className={`h-3.5 w-3.5 ${busy === op ? 'animate-spin' : ''}`} />
                {t(`action.${op}`)}
              </button>
            ))}
          {launchUrl && (
            <a
              href={launchUrl}
              target="_blank"
              rel="noreferrer"
              className="btn-primary inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-[12px] font-semibold"
            >
              <ExternalLink className="h-3.5 w-3.5" />
              {t('detail.launch')}
            </a>
          )}
        </div>
      </div>
    </div>
  );
}
