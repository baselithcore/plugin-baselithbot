'use client';

import { useRef } from 'react';
import { FileText, FileUp, Globe, Pencil, type LucideIcon } from 'lucide-react';
import { useTranslations } from 'next-intl';
import { cn } from '@/lib/cn';

export type IngestKind = 'url' | 'doc' | 'yaml';
export type SourceKind = 'manual' | IngestKind;
export type IngestPayload =
  | { kind: 'url'; url: string }
  | { kind: 'doc'; file: File }
  | { kind: 'yaml'; file: File };

const TAB_DEFS: Array<{
  key: SourceKind;
  icon: LucideIcon;
  labelKey: 'manual' | 'url' | 'doc' | 'yaml';
  hintKey: 'manualHint' | 'urlHint' | 'docHint' | 'yamlHint';
}> = [
  { key: 'manual', icon: Pencil, labelKey: 'manual', hintKey: 'manualHint' },
  { key: 'url', icon: Globe, labelKey: 'url', hintKey: 'urlHint' },
  { key: 'doc', icon: FileText, labelKey: 'doc', hintKey: 'docHint' },
  { key: 'yaml', icon: FileUp, labelKey: 'yaml', hintKey: 'yamlHint' },
];

const inputCls =
  'h-9 w-full rounded-md border border-border bg-bg-canvas px-3 text-xs text-text-primary outline-none transition-colors focus:border-status-info/60 focus:ring-2 focus:ring-status-info/20 placeholder:text-text-muted';

export function SourceTabs({
  source,
  onChange,
}: {
  source: SourceKind;
  onChange: (k: SourceKind) => void;
}) {
  const t = useTranslations('policies.source');
  return (
    <div
      role="tablist"
      aria-label={t('ariaLabel')}
      className="grid grid-cols-4 gap-1 rounded-lg border border-border bg-bg-canvas p-1"
    >
      {TAB_DEFS.map(({ key, icon: Icon, labelKey, hintKey }) => {
        const active = source === key;
        return (
          <button
            key={key}
            type="button"
            role="tab"
            aria-selected={active}
            onClick={() => onChange(key)}
            title={t(hintKey)}
            className={cn(
              'flex flex-col items-center gap-1 rounded-md px-2 py-2 text-[10.5px] font-medium transition-colors',
              active
                ? 'bg-status-info/15 text-status-info'
                : 'text-text-secondary hover:bg-bg-panel-elev hover:text-text-primary'
            )}
          >
            <Icon size={14} />
            <span>{t(labelKey)}</span>
          </button>
        );
      })}
    </div>
  );
}

export function UrlSourceInput({ url, onChange }: { url: string; onChange: (s: string) => void }) {
  const t = useTranslations('policies.source');
  return (
    <label className="block">
      <span className="mb-1 block text-[10px] uppercase tracking-wide text-text-muted">
        {t('urlInputLabel')}
        <span className="ml-1 normal-case text-text-faint">{t('urlInputHint')}</span>
      </span>
      <input
        type="url"
        value={url}
        onChange={(e) => onChange(e.target.value)}
        placeholder="https://..."
        className={inputCls}
        required
      />
    </label>
  );
}

export function FileSourceInput({
  kind,
  file,
  onChange,
}: {
  kind: 'doc' | 'yaml';
  file: File | null;
  onChange: (f: File | null) => void;
}) {
  const t = useTranslations('policies.source');
  const ref = useRef<HTMLInputElement>(null);
  const accept =
    kind === 'yaml'
      ? '.yaml,.yml,application/x-yaml,text/yaml'
      : '.pdf,.docx,.md,.txt,application/pdf';
  return (
    <label className="block">
      <span className="mb-1 block text-[10px] uppercase tracking-wide text-text-muted">
        {kind === 'yaml' ? t('fileYaml') : t('fileDoc')}
        <span className="ml-1 normal-case text-text-faint">
          · {kind === 'yaml' ? t('fileYamlHint') : t('fileDocHint')}
        </span>
      </span>
      <div className="flex items-center gap-2">
        <input
          ref={ref}
          type="file"
          accept={accept}
          onChange={(e) => onChange(e.target.files?.[0] ?? null)}
          className="hidden"
        />
        <button
          type="button"
          onClick={() => ref.current?.click()}
          className="inline-flex h-9 items-center gap-2 rounded-md border border-border bg-bg-canvas px-3 text-xs hover:bg-bg-panel-elev"
        >
          <FileUp size={13} /> {t('chooseFile')}
        </button>
        <span className="truncate text-xs text-text-muted">{file ? file.name : t('noFile')}</span>
      </div>
    </label>
  );
}
