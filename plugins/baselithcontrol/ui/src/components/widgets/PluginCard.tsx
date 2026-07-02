import { motion } from 'motion/react';
import { useTranslation } from 'react-i18next';
import {
  Box,
  ExternalLink,
  RefreshCw,
  Power,
  PlayCircle,
  Brain,
  Compass,
  ShieldAlert,
  HeartPulse,
  BookOpen,
  Cpu,
  TrendingUp,
  Briefcase,
  Layers,
  DollarSign,
} from 'lucide-react';
import type { LifecycleOp, PluginCard as Card } from '@/types';
import { formatTokens, formatUsd } from '@/lib/format';
import { itemVariants, spring } from '@/lib/motion';
import { useLifecycleAction } from '@/hooks/useLifecycleAction';
import { useControlStore } from '@/store/useControlStore';
import { HealthBadge } from './HealthBadge';

interface Props {
  card: Card;
  onOpen: (name: string) => void;
  canControl: boolean;
}

const OPS: { op: LifecycleOp; icon: typeof Power }[] = [
  { op: 'enable', icon: PlayCircle },
  { op: 'reload', icon: RefreshCw },
  { op: 'disable', icon: Power },
];

const OP_COLORS: Record<LifecycleOp, string> = {
  enable: 'hover:border-emerald-500/50 hover:text-emerald-500 hover:bg-emerald-500/10',
  reload:
    'hover:border-[var(--accent-border)] hover:text-[var(--accent)] hover:bg-[var(--accent-soft)]',
  disable: 'hover:border-rose-500/50 hover:text-rose-500 hover:bg-rose-500/10',
};

function getPluginIcon(card: Card) {
  const name = card.name.toLowerCase();
  const cat = card.category.toLowerCase();

  if (name.includes('jira')) return Briefcase;
  if (name.includes('scraper') || name.includes('scrape')) return Compass;
  if (
    name.includes('cve') ||
    name.includes('hunter') ||
    name.includes('honeypot') ||
    name.includes('red')
  )
    return ShieldAlert;
  if (name.includes('med')) return HeartPulse;
  if (name.includes('wiki')) return BookOpen;
  if (name.includes('brain') || name.includes('twin')) return Cpu;
  if (name.includes('optimize') || name.includes('process')) return TrendingUp;
  if (name.includes('agent') || cat.includes('agent')) return Brain;
  if (cat.includes('core')) return Layers;

  return Box;
}

export function PluginCard({ card, onOpen, canControl }: Props) {
  const { t } = useTranslation();
  // Shared confirm → run → patch → toast flow (same as the detail header).
  const { busy, act, disabledFor } = useLifecycleAction(card);
  const cost = useControlStore((s) => s.costByPlugin[card.name]);

  const standalone = card.surfaces.find((s) => s.embeddable && s.mount_url)?.mount_url;
  const embeddable = card.surfaces.some((s) => s.embeddable);
  const IconComponent = getPluginIcon(card);
  const muted = card.state === 'disabled';

  return (
    <motion.div
      layout
      variants={itemVariants}
      whileHover={{ y: -2 }}
      whileTap={{ scale: 0.995 }}
      transition={spring}
      className={`group glass glass-interactive relative flex min-h-[10rem] flex-col gap-2.5 overflow-hidden p-3.5 ${
        card.state === 'failed' ? 'border-rose-500/30' : ''
      } ${muted ? 'opacity-70 hover:opacity-100' : ''}`}
    >
      <button
        type="button"
        onClick={() => onOpen(card.name)}
        className="flex w-full cursor-pointer items-start justify-between gap-3 text-left"
      >
        <div className="flex min-w-0 items-center gap-3">
          <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg border brd bg-[var(--surface-inset)] t-dim transition group-hover:bg-[var(--accent-soft)] group-hover:text-[var(--accent)]">
            <IconComponent className="h-[18px] w-[18px]" />
          </span>
          <div className="min-w-0">
            <div className="font-display truncate text-[15px] font-bold tracking-tight t-primary transition group-hover:text-[var(--accent)]">
              {card.name}
            </div>
            <div className="text-[11px] font-medium tabular-nums t-faint">
              {t('card.version', { version: card.version })}
            </div>
          </div>
        </div>
        {/* Status + cost stack into the header's right column. The left column
            (icon + name + version) is taller than a lone status pill, so the
            cost KPI fills existing slack — it never adds a row to the card,
            keeping every card in a grid row the same height. */}
        <div className="flex shrink-0 flex-col items-end gap-1.5">
          <HealthBadge state={card.state} />
          {cost && cost.cost_usd > 0 && (
            <span
              className="inline-flex items-center gap-1 rounded-md border border-[var(--accent-border)] bg-[var(--accent-soft)] px-1.5 py-0.5 text-[10px] font-medium tabular-nums t-accent"
              title={t('card.llm_cost_hint', {
                tokens: formatTokens(cost.total_tokens),
                calls: cost.calls,
              })}
            >
              <DollarSign className="h-3 w-3" />
              {formatUsd(cost.cost_usd)}
            </span>
          )}
        </div>
      </button>

      <p className="line-clamp-2 min-h-[2.5rem] text-[12px] leading-relaxed t-dim">
        {card.description}
      </p>

      <div className="flex flex-wrap items-center gap-1.5 text-[10px] font-medium uppercase tracking-wide">
        {card.provides_routes && (
          <span className="rounded-md border brd px-1.5 py-0.5 t-dim">{t('card.routes')}</span>
        )}
        {embeddable && (
          <span className="rounded-md border brd px-1.5 py-0.5 t-dim">{t('card.embed')}</span>
        )}
        <span className="rounded-md border brd px-1.5 py-0.5 t-faint">{card.category}</span>
        <span
          className="rounded-md border brd px-1.5 py-0.5 t-faint"
          title={t(`card.tenancy_${card.tenancy}_hint`)}
        >
          {t(`card.tenancy_${card.tenancy}`)}
        </span>
        {standalone && (
          <a
            href={standalone}
            target="_blank"
            rel="noreferrer"
            onClick={(e) => e.stopPropagation()}
            title={t('card.open')}
            className="ml-auto inline-flex items-center gap-1 rounded-md border brd px-1.5 py-0.5 t-dim transition hover:border-[var(--accent-border)] hover:text-[var(--accent)]"
          >
            <ExternalLink className="h-3 w-3" />
            {t('card.open')}
          </a>
        )}
      </div>

      {canControl && (
        <div className="mt-auto flex gap-1.5 border-t brd pt-3">
          {OPS.map(({ op, icon: Icon }) => {
            // Inhibit no-op actions (shared matrix): enable when already
            // active, disable when already disabled, reload when not active.
            const opDisabled = disabledFor(op);
            return (
              <button
                key={op}
                type="button"
                disabled={opDisabled}
                onClick={() => act(op)}
                title={opDisabled && busy === null ? t(`action.${op}_disabled`) : t(`action.${op}`)}
                className={`flex flex-1 cursor-pointer items-center justify-center gap-1.5 rounded-lg border brd px-2 py-1.5 text-[11px] font-medium t-dim transition disabled:cursor-not-allowed disabled:opacity-40 disabled:hover:bg-transparent ${OP_COLORS[op]}`}
              >
                <Icon className={`h-3.5 w-3.5 ${busy === op ? 'animate-spin' : ''}`} />
                {t(`action.${op}`)}
              </button>
            );
          })}
        </div>
      )}
    </motion.div>
  );
}
