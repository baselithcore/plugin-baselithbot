import { useTranslation } from 'react-i18next';
import { Link as LinkIcon, Layers, Tag, ExternalLink, DollarSign } from 'lucide-react';
import type { PluginCard } from '@/types';
import { ConfigToggle } from '@/components/widgets/ConfigToggle';
import { useControlStore } from '@/store/useControlStore';
import { formatTokens, formatUsd } from '@/lib/format';

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
  const cost = useControlStore((s) => s.costByPlugin[card.name]);

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
    <div className="space-y-4">
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

      {/* Real measured LLM spend for this plugin, broken down by model. */}
      {cost && cost.cost_usd > 0 && (
        <div className="glass space-y-3 p-5">
          <div className="flex flex-wrap items-baseline justify-between gap-2">
            <h3 className="flex items-center gap-2 text-[11px] font-semibold uppercase tracking-wider t-faint">
              <DollarSign className="h-4 w-4 t-accent" />
              {t('detail.llm_cost')}
            </h3>
            <span className="text-[12px] t-dim">
              <span className="font-display text-lg font-bold t-accent">
                {formatUsd(cost.cost_usd)}
              </span>
              {' · '}
              {t('detail.cost_summary', {
                tokens: formatTokens(cost.total_tokens),
                calls: cost.calls,
              })}
            </span>
          </div>
          <div className="grid grid-cols-[1fr_auto_auto_auto] gap-x-3 border-b brd pb-1.5 text-[11px] font-semibold uppercase tracking-wide t-faint">
            <span>{t('cost.col_used_model')}</span>
            <span className="text-right">{t('cost.col_calls')}</span>
            <span className="text-right">{t('cost.col_tokens')}</span>
            <span className="text-right">{t('cost.col_cost')}</span>
          </div>
          {[...cost.rows]
            .sort((a, b) => b.cost_usd - a.cost_usd)
            .map((r) => (
              <div
                key={r.model}
                className="grid grid-cols-[1fr_auto_auto_auto] gap-x-3 text-[12.5px]"
              >
                <span className="truncate font-mono t-primary">{r.model}</span>
                <span className="text-right tabular-nums t-dim">{r.calls}</span>
                <span
                  className="text-right tabular-nums t-dim"
                  title={`${r.prompt_tokens} in / ${r.completion_tokens} out`}
                >
                  {formatTokens(r.total_tokens)}
                </span>
                <span className="text-right font-semibold tabular-nums t-primary">
                  {formatUsd(r.cost_usd)}
                </span>
              </div>
            ))}
          <p className="text-[11px] t-faint">{t('detail.cost_note')}</p>
        </div>
      )}
    </div>
  );
}
