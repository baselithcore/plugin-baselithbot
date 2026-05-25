import {
  Bookmark,
  Cpu,
  Palette,
  Settings as SettingsIcon,
  SlidersHorizontal,
  type LucideIcon,
} from 'lucide-react';
import { useEffect, useId, useMemo, useState } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { useDomain } from '../contexts/DomainContext';
import { cn } from '../lib/cn';
import { Button, ModalShell, SectionHeader, Switch } from './ui';
import { BrandingSection } from './settings/BrandingSection';
import { ObsidianSection } from './settings/ObsidianSection';
import { ProviderSection } from './settings/ProviderSection';

export interface Settings {
  retrievalLimit: number;
  showTrace: boolean;
  showTimer: boolean;
}

export const DEFAULT_SETTINGS: Settings = {
  retrievalLimit: 8,
  showTrace: true,
  showTimer: true,
};

const STORAGE_KEY = 'llm-wiki:settings';
const TAB_STORAGE_KEY = 'llm-wiki:settings-tab';

type TabKey = 'general' | 'branding' | 'provider' | 'obsidian';

interface TabSpec {
  key: TabKey;
  label: string;
  icon: LucideIcon;
}

export function readSettings(): Settings {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return DEFAULT_SETTINGS;
    const parsed = JSON.parse(raw) as Partial<Settings>;
    return { ...DEFAULT_SETTINGS, ...parsed };
  } catch {
    return DEFAULT_SETTINGS;
  }
}

export function saveSettings(s: Settings) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(s));
  } catch {
    /* storage disabled */
  }
}

interface Props {
  open: boolean;
  onClose: () => void;
  settings: Settings;
  onChange: (s: Settings) => void;
}

export function SettingsModal({ open, onClose, settings, onChange }: Props) {
  const patch = (partial: Partial<Settings>) => onChange({ ...settings, ...partial });
  const { branding } = useDomain();
  const { can } = useAuth();
  const isAdmin = can('admin.tenant.manage');
  const tenantName = branding?.tenant?.name ?? branding?.domain ?? null;

  const tabs: TabSpec[] = useMemo(() => {
    const list: TabSpec[] = [{ key: 'general', label: 'Generale', icon: SlidersHorizontal }];
    if (isAdmin && tenantName) list.push({ key: 'branding', label: 'Branding', icon: Palette });
    if (isAdmin) list.push({ key: 'provider', label: 'Provider LLM', icon: Cpu });
    if (isAdmin && tenantName) list.push({ key: 'obsidian', label: 'Obsidian', icon: Bookmark });
    return list;
  }, [isAdmin, tenantName]);

  const [tab, setTab] = useState<TabKey>(() => {
    try {
      const stored = localStorage.getItem(TAB_STORAGE_KEY) as TabKey | null;
      return stored ?? 'general';
    } catch {
      return 'general';
    }
  });

  // If the active tab disappears (e.g. admin permission revoked, tenant
  // unmounted), fall back to a visible one so the panel never stays
  // blank.
  useEffect(() => {
    if (!tabs.some((t) => t.key === tab)) setTab(tabs[0]?.key ?? 'general');
  }, [tabs, tab]);

  const handleTabChange = (next: TabKey) => {
    setTab(next);
    try {
      localStorage.setItem(TAB_STORAGE_KEY, next);
    } catch {
      /* ignore */
    }
  };

  const footer = (
    <div className="flex items-center justify-between gap-3">
      <span className="text-[10px] text-ink-subtle">
        Le preferenze interfaccia sono salvate sul browser.
      </span>
      <Button variant="secondary" onClick={() => onChange(DEFAULT_SETTINGS)} className="!text-[11px]">
        Ripristina predefiniti
      </Button>
    </div>
  );

  return (
    <ModalShell
      open={open}
      onClose={onClose}
      title="Impostazioni"
      icon={SettingsIcon}
      width="2xl"
      panelClassName="h-[min(85vh,720px)]"
      footer={footer}
    >
      <div
        role="tablist"
        aria-label="Sezioni impostazioni"
        className="flex shrink-0 items-center gap-1 overflow-x-auto border-b border-[var(--color-border)] bg-[var(--color-canvas)] px-3 py-2"
      >
        {tabs.map((t) => {
          const Icon = t.icon;
          const active = tab === t.key;
          return (
            <button
              key={t.key}
              role="tab"
              type="button"
              aria-selected={active}
              aria-controls={`settings-panel-${t.key}`}
              id={`settings-tab-${t.key}`}
              onClick={() => handleTabChange(t.key)}
              className={cn(
                'focus-ring inline-flex shrink-0 items-center gap-1.5 rounded-md px-2.5 py-1.5 text-[11.5px] font-medium transition-colors',
                active
                  ? 'bg-[var(--color-brand-soft)] text-[var(--color-brand)]'
                  : 'text-ink-muted hover:bg-[var(--color-surface)] hover:text-ink'
              )}
            >
              <Icon size={12} aria-hidden />
              {t.label}
            </button>
          );
        })}
      </div>

      <div
        id={`settings-panel-${tab}`}
        role="tabpanel"
        aria-labelledby={`settings-tab-${tab}`}
        className="min-h-0 flex-1 overflow-y-auto overscroll-contain px-5 py-4"
      >
        {tab === 'general' && <GeneralPanel settings={settings} patch={patch} />}
        {tab === 'branding' && tenantName && <BrandingSection tenant={tenantName} />}
        {tab === 'provider' && <ProviderSection />}
        {tab === 'obsidian' && tenantName && <ObsidianSection tenant={tenantName} />}
      </div>
    </ModalShell>
  );
}

function GeneralPanel({
  settings,
  patch,
}: {
  settings: Settings;
  patch: (partial: Partial<Settings>) => void;
}) {
  return (
    <div className="space-y-5">
      <section>
        <SectionHeader title="Retrieval" />
        <div className="flex flex-col gap-3">
          <Row
            label="Numero di fonti per risposta"
            hint="Più fonti = più contesto disponibile, ma risposte leggermente più lente."
          >
            <RangeControl
              value={settings.retrievalLimit}
              min={3}
              max={20}
              onChange={(v) => patch({ retrievalLimit: v })}
              label="numero fonti"
            />
          </Row>
        </div>
      </section>

      <section>
        <SectionHeader title="Interfaccia" />
        <div className="flex flex-col gap-3">
          <Row
            label="Mostra fasi dell'assistente"
            hint="Visualizza recupero e sintesi durante la generazione."
          >
            <Switch
              checked={settings.showTrace}
              onChange={(v) => patch({ showTrace: v })}
              label="mostra fasi"
              hideLabel
            />
          </Row>
          <Row label="Mostra tempo di risposta" hint="Tempo al primo token e tempo totale.">
            <Switch
              checked={settings.showTimer}
              onChange={(v) => patch({ showTimer: v })}
              label="mostra tempo"
              hideLabel
            />
          </Row>
        </div>
      </section>
    </div>
  );
}

function Row({
  label,
  hint,
  children,
}: {
  label: string;
  hint?: string;
  children: React.ReactNode;
}) {
  const hintId = useId();
  return (
    <div className="flex items-start justify-between gap-4">
      <div className="min-w-0">
        <div className="text-xs font-medium text-ink">{label}</div>
        {hint && (
          <div id={hintId} className="mt-0.5 text-[10.5px] leading-relaxed text-ink-subtle">
            {hint}
          </div>
        )}
      </div>
      <div className="shrink-0" aria-describedby={hint ? hintId : undefined}>
        {children}
      </div>
    </div>
  );
}

function RangeControl({
  value,
  min,
  max,
  onChange,
  label,
}: {
  value: number;
  min: number;
  max: number;
  onChange: (v: number) => void;
  label: string;
}) {
  return (
    <div className="flex min-w-[180px] items-center gap-3">
      <input
        type="range"
        min={min}
        max={max}
        step={1}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        aria-label={label}
        aria-valuenow={value}
        className="flex-1 accent-[var(--color-brand)]"
      />
      <span className="w-6 text-right text-xs font-medium tabular-nums text-ink">{value}</span>
    </div>
  );
}
