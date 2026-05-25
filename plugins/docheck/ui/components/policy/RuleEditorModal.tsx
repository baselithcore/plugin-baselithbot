'use client';

import { useEffect, useState } from 'react';
import * as Dialog from '@radix-ui/react-dialog';
import { Loader2, X } from 'lucide-react';
import { useTranslations } from 'next-intl';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/cn';
import type { RulePayload, RuleRow } from '@/lib/api';

const RULE_TYPES: RulePayload['rule_type'][] = [
  'presence',
  'absence',
  'format',
  'numeric_limit',
  'semantic',
];
const SEVERITIES: RulePayload['severity'][] = ['fail', 'warn', 'info'];

interface Props {
  open: boolean;
  mode: 'create' | 'edit';
  initial?: RuleRow | null;
  busy?: boolean;
  onClose: () => void;
  onSubmit: (payload: RulePayload) => void | Promise<void>;
}

export function RuleEditorModal({ open, mode, initial, busy, onClose, onSubmit }: Props) {
  const t = useTranslations('policies.ruleEditor');
  const [form, setForm] = useState<RulePayload>({
    rule_type: 'presence',
    severity: 'warn',
    excerpt: '',
  });
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    if (!open) return;
    setErr(null);
    setForm(
      initial
        ? {
            id: initial.id,
            rule_type: initial.rule_type,
            severity: initial.severity,
            excerpt: initial.excerpt,
            matcher: initial.matcher ?? null,
          }
        : {
            rule_type: 'presence',
            severity: 'warn',
            excerpt: '',
            matcher: null,
          }
    );
  }, [open, initial]);

  async function submit() {
    setErr(null);
    if (!form.excerpt.trim()) {
      setErr(t('errExcerpt'));
      return;
    }
    try {
      await onSubmit({
        ...form,
        excerpt: form.excerpt.trim(),
        matcher: form.matcher || null,
      });
    } catch (ex) {
      setErr(ex instanceof Error ? ex.message : String(ex));
    }
  }

  return (
    <Dialog.Root
      open={open}
      onOpenChange={(v) => {
        if (!v) onClose();
      }}
    >
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-40 bg-bg-canvas/70 backdrop-blur-sm animate-fade-in" />
        <Dialog.Content
          className="fixed left-1/2 top-1/2 z-50 w-[min(560px,94vw)] surface-elev rounded-xl border border-border shadow-popover animate-dialog-in overflow-hidden flex flex-col"
          style={{ transform: 'translate(-50%, -50%)' }}
        >
          <header className="flex items-center justify-between border-b border-border px-5 py-4">
            <div>
              <div className="text-[10px] uppercase tracking-[0.2em] text-text-muted">
                {mode === 'create' ? t('createEyebrow') : t('editEyebrow')}
              </div>
              <Dialog.Title className="mt-1 text-base font-semibold">
                {mode === 'create' ? t('createTitle') : initial?.id}
              </Dialog.Title>
            </div>
            <button
              type="button"
              onClick={onClose}
              aria-label={t('close')}
              className="rounded-md p-1.5 text-text-muted hover:bg-bg-panel-elev hover:text-text-primary"
            >
              <X size={16} />
            </button>
          </header>

          <div className="px-5 py-4 space-y-4">
            {mode === 'create' && (
              <Field label={t('ruleId')} hint={t('ruleIdHint')}>
                <input
                  value={form.id ?? ''}
                  onChange={(e) =>
                    setForm({
                      ...form,
                      id: e.target.value.toLowerCase() || undefined,
                    })
                  }
                  className={inputClass}
                />
              </Field>
            )}

            <div className="grid grid-cols-2 gap-3">
              <Field label={t('type')}>
                <select
                  value={form.rule_type}
                  onChange={(e) =>
                    setForm({
                      ...form,
                      rule_type: e.target.value as RulePayload['rule_type'],
                    })
                  }
                  className={inputClass}
                >
                  {RULE_TYPES.map((r) => (
                    <option key={r} value={r}>
                      {r}
                    </option>
                  ))}
                </select>
              </Field>
              <Field label={t('severity')}>
                <select
                  value={form.severity}
                  onChange={(e) =>
                    setForm({
                      ...form,
                      severity: e.target.value as RulePayload['severity'],
                    })
                  }
                  className={inputClass}
                >
                  {SEVERITIES.map((s) => (
                    <option key={s} value={s}>
                      {s}
                    </option>
                  ))}
                </select>
              </Field>
            </div>

            <Field label={t('excerpt')}>
              <textarea
                value={form.excerpt}
                onChange={(e) => setForm({ ...form, excerpt: e.target.value })}
                rows={4}
                className={cn(inputClass, 'h-auto py-2 font-mono text-[11px] leading-5')}
                required
              />
            </Field>

            <Field label={t('matcher')} hint={t('matcherHint')}>
              <input
                value={form.matcher ?? ''}
                onChange={(e) => setForm({ ...form, matcher: e.target.value || null })}
                className={cn(inputClass, 'font-mono text-[11px]')}
              />
            </Field>

            {err && (
              <div className="rounded-md border border-status-danger/40 bg-status-danger/10 px-3 py-2 text-xs text-status-danger">
                {err}
              </div>
            )}
          </div>

          <footer className="flex justify-end gap-2 border-t border-border px-5 py-3">
            <Button variant="ghost" size="sm" onClick={onClose} disabled={busy}>
              {t('cancel')}
            </Button>
            <Button variant="primary" size="sm" onClick={submit} disabled={busy}>
              {busy && <Loader2 size={13} className="animate-spin" />}
              {mode === 'create' ? t('addRule') : t('saveRule')}
            </Button>
          </footer>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}

const inputClass =
  'h-9 w-full rounded-md border border-border bg-bg-canvas px-3 text-xs text-text-primary outline-none transition-colors focus:border-status-info/60 focus:ring-2 focus:ring-status-info/20 placeholder:text-text-muted';

function Field({
  label,
  hint,
  children,
}: {
  label: string;
  hint?: string;
  children: React.ReactNode;
}) {
  return (
    <label className="block">
      <span className="mb-1 block text-[10px] uppercase tracking-wide text-text-muted">
        {label}
        {hint && <span className="ml-1 text-text-faint normal-case">· {hint}</span>}
      </span>
      {children}
    </label>
  );
}
