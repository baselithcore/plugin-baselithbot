'use client';

import {
  CheckCircle2,
  FlaskConical,
  Languages,
  Layers,
  ShieldAlert,
  Target,
  type LucideIcon,
} from 'lucide-react';
import { useTranslations } from 'next-intl';
import { Card, CardContent } from '@/components/ui/card';
import { cn } from '@/lib/cn';
import { StepHeader } from './StepHeader';
import { LANGS, type ScanProfile, type SevFloor } from './types';

export function OptionsCard({
  profile,
  onChange,
}: {
  profile: ScanProfile;
  onChange: (p: ScanProfile) => void;
}) {
  const t = useTranslations('scan.options');
  return (
    <Card>
      <CardContent className="pt-5">
        <StepHeader idx={3} icon={FlaskConical} title={t('title')} hint={t('hint')} />
        <div className="grid gap-3">
          <Field icon={Languages} label={t('language')}>
            <select
              value={profile.lang}
              onChange={(e) => onChange({ ...profile, lang: e.target.value })}
              className="w-full rounded-md border border-border bg-bg-canvas px-2.5 py-1.5 text-xs ring-focus"
            >
              {LANGS.map((l) => (
                <option key={l.code} value={l.code}>
                  {l.label}
                </option>
              ))}
            </select>
          </Field>

          <Field icon={ShieldAlert} label={t('severityFloor')}>
            <div className="flex rounded-md border border-border bg-bg-canvas p-0.5">
              {(['INFO', 'WARN', 'FAIL'] as SevFloor[]).map((s) => (
                <button
                  key={s}
                  type="button"
                  onClick={() => onChange({ ...profile, severityFloor: s })}
                  className={cn(
                    'flex-1 px-2.5 py-1 rounded text-[11px] font-medium transition-colors',
                    profile.severityFloor === s
                      ? 'bg-bg-panel-elev text-text-primary'
                      : 'text-text-muted hover:text-text-primary'
                  )}
                >
                  {s}+
                </button>
              ))}
            </div>
          </Field>

          <Field
            icon={Target}
            label={t('confidenceMin', {
              pct: (profile.confidenceMin * 100).toFixed(0),
            })}
          >
            <input
              type="range"
              min={0}
              max={100}
              value={profile.confidenceMin * 100}
              onChange={(e) =>
                onChange({
                  ...profile,
                  confidenceMin: Number(e.target.value) / 100,
                })
              }
              className="w-full accent-status-info"
            />
          </Field>

          <ToggleRow
            icon={CheckCircle2}
            label={t('includePass')}
            hint={t('includePassHint')}
            value={profile.includePass}
            onChange={(v) => onChange({ ...profile, includePass: v })}
          />
          <ToggleRow
            icon={Layers}
            label={t('groupByPolicy')}
            hint={t('groupByPolicyHint')}
            value={profile.groupByPolicy}
            onChange={(v) => onChange({ ...profile, groupByPolicy: v })}
          />
        </div>
      </CardContent>
    </Card>
  );
}

function Field({
  icon: Icon,
  label,
  children,
}: {
  icon: LucideIcon;
  label: string;
  children: React.ReactNode;
}) {
  return (
    <div>
      <div className="flex items-center gap-1.5 mb-1.5 text-[11px] font-medium text-text-secondary">
        <Icon size={11} className="text-text-muted" />
        {label}
      </div>
      {children}
    </div>
  );
}

function ToggleRow({
  icon: Icon,
  label,
  hint,
  value,
  onChange,
}: {
  icon: LucideIcon;
  label: string;
  hint?: string;
  value: boolean;
  onChange: (v: boolean) => void;
}) {
  return (
    <button
      type="button"
      onClick={() => onChange(!value)}
      className="flex items-center gap-3 rounded-md border border-border bg-bg-canvas px-3 py-2 text-left hover:border-border-strong transition-colors"
    >
      <Icon size={13} className={value ? 'text-status-info' : 'text-text-muted'} />
      <div className="min-w-0 flex-1">
        <div className="text-xs font-medium">{label}</div>
        {hint && <div className="text-[10px] text-text-muted">{hint}</div>}
      </div>
      <span
        className={cn(
          'h-4 w-7 rounded-full border transition-colors relative',
          value ? 'bg-status-info border-status-info' : 'bg-bg-panel border-border'
        )}
      >
        <span
          className={cn(
            'absolute top-0.5 h-2.5 w-2.5 rounded-full bg-white transition-all',
            value ? 'left-3' : 'left-0.5'
          )}
        />
      </span>
    </button>
  );
}
