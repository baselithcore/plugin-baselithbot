import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { runAction, setPluginConfig } from '@/lib/api';
import { useUiStore } from '@/store/useUiStore';
import { useControlStore } from '@/store/useControlStore';
import type { LifecycleOp, PluginCard } from '@/types';

export interface LifecycleAction {
  /** The op currently in flight, or null when idle. */
  busy: LifecycleOp | null;
  /** Confirm → run → optimistic store patch → toast. */
  act: (op: LifecycleOp) => Promise<void>;
  /** No-op inhibition matrix (enable when active, reload when inactive, …). */
  disabledFor: (op: LifecycleOp) => boolean;
}

/**
 * Shared lifecycle action flow for a plugin card. Used by both the grid card
 * and the detail header so the confirm/run/patch/toast sequence and the
 * disabled matrix never drift between the two surfaces.
 */
export function useLifecycleAction(card: PluginCard): LifecycleAction {
  const { t } = useTranslation();
  const ask = useUiStore((s) => s.ask);
  const pushToast = useUiStore((s) => s.pushToast);
  const patchPlugin = useControlStore((s) => s.patchPlugin);
  const [busy, setBusy] = useState<LifecycleOp | null>(null);

  const act = async (op: LifecycleOp) => {
    if (!(await ask(t('action.confirm', { op, plugin: card.name })))) return;
    setBusy(op);
    try {
      // enable/disable persist to plugins.yaml (durable across restarts) and
      // sync the runtime; reload is a transient runtime op. All reflect on the
      // card immediately via the store patch.
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

  return { busy, act, disabledFor };
}
