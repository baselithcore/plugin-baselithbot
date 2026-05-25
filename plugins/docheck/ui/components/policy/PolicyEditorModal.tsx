'use client';

import { useEffect, useState } from 'react';
import * as Dialog from '@radix-ui/react-dialog';
import { Loader2, X } from 'lucide-react';
import { useTranslations } from 'next-intl';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import { cn } from '@/lib/cn';
import type { PolicyRow, RulePayload } from '@/lib/api';
import {
  FileSourceInput,
  SourceTabs,
  UrlSourceInput,
  type IngestPayload,
  type SourceKind,
} from './PolicySourcePicker';

export type { IngestPayload } from './PolicySourcePicker';

const SCOPES: PolicyRow['scope'][] = ['global_default', 'eu', 'world', 'custom'];
const LANGS = ['it', 'en', 'fr', 'de', 'es'];

export interface PolicyMetaForm {
  id: string;
  version: string;
  title: string;
  scope: PolicyRow['scope'];
  lang: string;
  active: boolean;
}

interface Props {
  open: boolean;
  mode: 'create' | 'edit';
  initial?: Partial<PolicyMetaForm>;
  /** Edit mode locks id/version (immutable PK). */
  busy?: boolean;
  /** Optional initial first rule used only in create mode. */
  initialRule?: RulePayload | null;
  /** Progress state for ingestion (file upload + LLM extraction). */
  progress?: { phase: 'uploading' | 'processing'; pct: number } | null;
  onClose: () => void;
  onSubmit: (form: PolicyMetaForm, firstRule: RulePayload | null) => void | Promise<void>;
  /** Required when mode === "create" to support URL/file ingestion sources. */
  onIngest?: (payload: IngestPayload) => void | Promise<void>;
}

export function PolicyEditorModal({
  open,
  mode,
  initial,
  busy,
  initialRule,
  progress,
  onClose,
  onSubmit,
  onIngest,
}: Props) {
  const t = useTranslations('policies.policyEditor');
  const [form, setForm] = useState<PolicyMetaForm>({
    id: '',
    version: '1.0.0',
    title: '',
    scope: 'custom',
    lang: 'it',
    active: false,
  });
  const [includeRule, setIncludeRule] = useState(false);
  const [rule, setRule] = useState<RulePayload>({
    rule_type: 'presence',
    severity: 'warn',
    excerpt: '',
  });
  const [err, setErr] = useState<string | null>(null);
  const [source, setSource] = useState<SourceKind>('manual');
  const [url, setUrl] = useState('');
  const [file, setFile] = useState<File | null>(null);

  useEffect(() => {
    if (!open) return;
    setErr(null);
    setSource('manual');
    setUrl('');
    setFile(null);
    setForm({
      id: initial?.id ?? '',
      version: initial?.version ?? '1.0.0',
      title: initial?.title ?? '',
      scope: initial?.scope ?? 'custom',
      lang: initial?.lang ?? 'it',
      active: initial?.active ?? false,
    });
    setIncludeRule(!!initialRule);
    setRule(initialRule ?? { rule_type: 'presence', severity: 'warn', excerpt: '' });
  }, [open, initial, initialRule]);

  function set<K extends keyof PolicyMetaForm>(k: K, v: PolicyMetaForm[K]) {
    setForm((f) => ({ ...f, [k]: v }));
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setErr(null);
    try {
      if (mode === 'create' && source !== 'manual') {
        if (!onIngest) {
          setErr(t('errSourceUnsupported'));
          return;
        }
        if (source === 'url') {
          const u = url.trim();
          if (!/^https?:\/\//i.test(u)) {
            setErr(t('errInvalidUrl'));
            return;
          }
          await onIngest({ kind: 'url', url: u });
        } else {
          if (!file) {
            setErr(t('errSelectFile'));
            return;
          }
          await onIngest({ kind: source, file });
        }
        return;
      }
      if (!form.id.match(/^[a-z0-9_.-]{2,64}$/)) {
        setErr(t('errId'));
        return;
      }
      if (!form.version.match(/^[a-zA-Z0-9._-]{1,32}$/)) {
        setErr(t('errVersion'));
        return;
      }
      if (!form.title.trim()) {
        setErr(t('errTitle'));
        return;
      }
      const firstRule =
        includeRule && rule.excerpt.trim() ? { ...rule, excerpt: rule.excerpt.trim() } : null;
      await onSubmit(form, firstRule);
    } catch (ex) {
      setErr(ex instanceof Error ? ex.message : String(ex));
    }
  }

  const ctaLabel =
    mode === 'edit'
      ? t('ctaSave')
      : source === 'manual'
        ? t('ctaCreate')
        : source === 'url'
          ? t('ctaImportUrl')
          : source === 'yaml'
            ? t('ctaImportYaml')
            : t('ctaExtractDoc');

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
          className="fixed left-1/2 top-1/2 z-50 w-[min(640px,94vw)] max-h-[92vh] surface-elev rounded-xl border border-border shadow-popover animate-dialog-in overflow-hidden flex flex-col"
          style={{ transform: 'translate(-50%, -50%)' }}
        >
          <header className="flex items-center justify-between border-b border-border px-5 py-4">
            <div>
              <div className="text-[10px] uppercase tracking-[0.2em] text-text-muted">
                {mode === 'create' ? t('createEyebrow') : t('editEyebrow')}
              </div>
              <Dialog.Title className="mt-1 text-base font-semibold">
                {mode === 'create' ? t('createTitle') : `${form.id}@${form.version}`}
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

          {(busy || progress) && (
            <div className="border-b border-border bg-bg-panel-soft px-5 py-2">
              <div className="flex items-center justify-between text-[10px] uppercase tracking-wide text-text-muted">
                <span>
                  {progress?.phase === 'uploading'
                    ? t('progressUploading')
                    : t('progressProcessing')}
                </span>
                {progress?.phase === 'uploading' && (
                  <span className="tabular-nums">{progress.pct}%</span>
                )}
              </div>
              <Progress
                className="mt-1.5"
                value={progress?.phase === 'uploading' ? progress.pct : 0}
                indeterminate={progress?.phase !== 'uploading'}
              />
            </div>
          )}

          <form onSubmit={submit} className="flex-1 overflow-auto px-5 py-4 space-y-4">
            {mode === 'create' && onIngest && (
              <SourceTabs
                source={source}
                onChange={(k) => {
                  setSource(k);
                  setErr(null);
                }}
              />
            )}

            {mode === 'create' && source === 'url' && (
              <UrlSourceInput url={url} onChange={setUrl} />
            )}

            {mode === 'create' && (source === 'doc' || source === 'yaml') && (
              <FileSourceInput kind={source} file={file} onChange={setFile} />
            )}

            {!(mode === 'create' && source !== 'manual') && (
              <>
                <div className="grid grid-cols-2 gap-3">
                  <Field label={t('policyId')} hint={t('policyIdHint')}>
                    <input
                      value={form.id}
                      onChange={(e) => set('id', e.target.value.toLowerCase())}
                      disabled={mode === 'edit'}
                      className={inputClass}
                      required
                    />
                  </Field>
                  <Field label={t('version')} hint={t('versionHint')}>
                    <input
                      value={form.version}
                      onChange={(e) => set('version', e.target.value)}
                      disabled={mode === 'edit'}
                      className={inputClass}
                      required
                    />
                  </Field>
                </div>

                <Field label={t('title')}>
                  <input
                    value={form.title}
                    onChange={(e) => set('title', e.target.value)}
                    className={inputClass}
                    required
                  />
                </Field>

                <div className="grid grid-cols-3 gap-3">
                  <Field label={t('scope')}>
                    <select
                      value={form.scope}
                      onChange={(e) => set('scope', e.target.value as PolicyRow['scope'])}
                      className={inputClass}
                    >
                      {SCOPES.map((s) => (
                        <option key={s} value={s}>
                          {s}
                        </option>
                      ))}
                    </select>
                  </Field>
                  <Field label={t('lang')}>
                    <select
                      value={form.lang}
                      onChange={(e) => set('lang', e.target.value)}
                      className={inputClass}
                    >
                      {LANGS.map((l) => (
                        <option key={l} value={l}>
                          {l.toUpperCase()}
                        </option>
                      ))}
                    </select>
                  </Field>
                  <Field label={t('status')}>
                    <label className="flex h-9 items-center gap-2 rounded-md border border-border bg-bg-canvas px-3 text-xs">
                      <input
                        type="checkbox"
                        checked={form.active}
                        onChange={(e) => set('active', e.target.checked)}
                      />
                      <span>{t('active')}</span>
                    </label>
                  </Field>
                </div>

                {mode === 'create' && (
                  <div className="rounded-md border border-border bg-bg-panel-soft p-3">
                    <label className="flex items-center gap-2 text-xs">
                      <input
                        type="checkbox"
                        checked={includeRule}
                        onChange={(e) => setIncludeRule(e.target.checked)}
                      />
                      <span className="font-medium">{t('includeFirstRule')}</span>
                    </label>
                    {includeRule && (
                      <div className="mt-3 space-y-2">
                        <div className="grid grid-cols-2 gap-2">
                          <select
                            value={rule.rule_type}
                            onChange={(e) =>
                              setRule({
                                ...rule,
                                rule_type: e.target.value as RulePayload['rule_type'],
                              })
                            }
                            className={inputClass}
                          >
                            {(
                              [
                                'presence',
                                'absence',
                                'format',
                                'numeric_limit',
                                'semantic',
                              ] as const
                            ).map((r) => (
                              <option key={r} value={r}>
                                {r}
                              </option>
                            ))}
                          </select>
                          <select
                            value={rule.severity}
                            onChange={(e) =>
                              setRule({
                                ...rule,
                                severity: e.target.value as RulePayload['severity'],
                              })
                            }
                            className={inputClass}
                          >
                            <option value="fail">fail</option>
                            <option value="warn">warn</option>
                            <option value="info">info</option>
                          </select>
                        </div>
                        <textarea
                          placeholder={t('excerptPlaceholder')}
                          value={rule.excerpt}
                          onChange={(e) => setRule({ ...rule, excerpt: e.target.value })}
                          rows={3}
                          className={cn(inputClass, 'h-auto py-2 font-mono text-[11px]')}
                        />
                        <input
                          placeholder={t('matcherPlaceholder')}
                          value={rule.matcher ?? ''}
                          onChange={(e) =>
                            setRule({
                              ...rule,
                              matcher: e.target.value || null,
                            })
                          }
                          className={cn(inputClass, 'font-mono text-[11px]')}
                        />
                      </div>
                    )}
                  </div>
                )}
              </>
            )}

            {err && (
              <div className="rounded-md border border-status-danger/40 bg-status-danger/10 px-3 py-2 text-xs text-status-danger">
                {err}
              </div>
            )}
          </form>

          <footer className="flex justify-end gap-2 border-t border-border px-5 py-3">
            <Button type="button" variant="ghost" size="sm" onClick={onClose} disabled={busy}>
              {t('cancel')}
            </Button>
            <Button
              type="button"
              variant="primary"
              size="sm"
              disabled={busy}
              onClick={(e) => submit(e as unknown as React.FormEvent)}
            >
              {busy && <Loader2 size={13} className="animate-spin" />}
              {ctaLabel}
            </Button>
          </footer>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}

const inputClass =
  'h-9 w-full rounded-md border border-border bg-bg-canvas px-3 text-xs text-text-primary outline-none transition-colors focus:border-status-info/60 focus:ring-2 focus:ring-status-info/20 placeholder:text-text-muted disabled:opacity-60';

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
