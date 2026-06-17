import { useTranslation } from 'react-i18next';
import { Link as LinkIcon, Layers, Tag, ExternalLink } from 'lucide-react';
import type { PluginCard } from '@/types';
import { ConfigToggle } from '@/components/widgets/ConfigToggle';

interface Props {
  card: PluginCard;
  surfaceLabel: string;
  canControl: boolean;
}

// Identity & configuration pane. A flat definition list (icon · key · value)
// replaces the old cramped flex rows; values right-aligned and monospaced where
// they're identifiers. Config lives here as a sibling card, not a stray block.
export function OverviewTab({ card, surfaceLabel, canControl }: Props) {
  const { t } = useTranslation();

  const rows = [
    {
      icon: <LinkIcon className="h-4 w-4 shrink-0 t-faint" />,
      label: t('detail.routes_prefix'),
      value: card.router_prefix ?? '—',
      mono: true,
    },
    {
      icon: <Layers className="h-4 w-4 shrink-0 t-faint" />,
      label: t('card.group'),
      value: card.group,
    },
    {
      icon: <Tag className="h-4 w-4 shrink-0 t-faint" />,
      label: t('detail.category'),
      value: card.category,
    },
    {
      icon: <ExternalLink className="h-4 w-4 shrink-0 t-faint" />,
      label: t('detail.surface'),
      value: surfaceLabel,
    },
  ];

  return (
    <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
      <div className="glass space-y-4 p-5 lg:col-span-2">
        <h3 className="text-[11px] font-semibold uppercase tracking-wider t-faint">
          {t('detail.profile')}
        </h3>
        <p className="text-[13px] leading-relaxed t-dim">{card.description}</p>

        <dl className="divide-y brd border-t brd">
          {rows.map((r) => (
            <div key={r.label} className="flex items-center justify-between gap-3 py-2.5">
              <dt className="flex items-center gap-2.5 text-[13px] t-dim">
                {r.icon}
                {r.label}
              </dt>
              <dd
                className={`truncate pl-2 text-right text-[13px] font-medium ${
                  r.mono ? 'font-mono text-xs t-accent' : 't-primary'
                }`}
              >
                {r.value}
              </dd>
            </div>
          ))}
        </dl>
      </div>

      <ConfigToggle plugin={card.name} enabled={card.config_enabled} canControl={canControl} />
    </div>
  );
}
