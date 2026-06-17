import { MonitorUp, Radio, Route, ShieldCheck, ShieldOff } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import type { PluginCard as Card } from '@/types';

interface Props {
  cards: Card[];
  connected: boolean;
  eventsCount: number;
  readOnly: boolean;
}

// Compact operational insights row. Frameless — the caller frames it together
// with the HeadBand KPIs as one unified metrics panel.
export function ControlInsights({ cards, connected, readOnly }: Props) {
  const { t } = useTranslation();
  const routes = cards.filter((c) => c.provides_routes).length;
  const interfaces = cards.filter((c) => c.surfaces.some((s) => s.embeddable)).length;
  const Shield = readOnly ? ShieldOff : ShieldCheck;

  const items = [
    {
      key: 'stream',
      icon: Radio,
      label: t('insight.stream'),
      value: connected ? t('status.live') : t('status.offline'),
      tone: connected ? 'text-emerald-500' : 'text-amber-500',
    },
    {
      key: 'routes',
      icon: Route,
      label: t('insight.routes'),
      value: routes.toLocaleString(),
      tone: 't-primary',
    },
    {
      key: 'interfaces',
      icon: MonitorUp,
      label: t('insight.interfaces'),
      value: interfaces.toLocaleString(),
      tone: 't-primary',
    },
    {
      key: 'access',
      icon: Shield,
      label: t('insight.access'),
      value: readOnly ? t('access.read_only') : t('access.admin'),
      tone: readOnly ? 'text-amber-500' : 'text-emerald-500',
    },
  ];

  return (
    <>
      {items.map(({ key, icon: Icon, label, value, tone }) => (
        <div
          key={key}
          className="flex items-center justify-between gap-2 bg-[var(--surface-1)] px-4 py-2.5"
        >
          <div className="flex min-w-0 items-center gap-1.5 text-[10px] font-medium uppercase tracking-wide t-faint">
            <Icon className="h-3 w-3 shrink-0" />
            <span className="truncate">{label}</span>
          </div>
          <div className={`shrink-0 truncate text-[13px] font-semibold ${tone}`}>{value}</div>
        </div>
      ))}
    </>
  );
}
