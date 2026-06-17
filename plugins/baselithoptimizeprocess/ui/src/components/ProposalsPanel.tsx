import { Check, Lightbulb, Sparkles, TrendingUp, X } from 'lucide-react';
import { AnimatePresence, motion, useReducedMotion } from 'motion/react';
import { useState } from 'react';

import { api } from '../api/client';
import type { OptimizationProposal } from '../api/types';
import { cn, formatNumber } from '../lib/ui';

interface ProposalsPanelProps {
  processId: string;
  proposals: OptimizationProposal[];
  busy: boolean;
  onOptimize: () => void;
  onDecision: (updated: OptimizationProposal) => void;
}

const STATUS_CHIP: Record<string, string> = {
  proposed: 'bg-accent/15 text-accent-soft',
  approved: 'bg-sev-low/15 text-sev-low',
  rejected: 'bg-slate-500/15 text-slate-400',
  applied: 'bg-indigo-400/15 text-indigo-300',
};

/** Human-in-the-loop optimization proposals with approve/reject controls. */
export function ProposalsPanel({
  processId,
  proposals,
  busy,
  onOptimize,
  onDecision,
}: ProposalsPanelProps) {
  const [deciding, setDeciding] = useState<string | null>(null);
  const reduceMotion = useReducedMotion();

  async function decide(id: string, approve: boolean) {
    setDeciding(id);
    try {
      onDecision(await api.decideProposal(id, approve));
    } finally {
      setDeciding(null);
    }
  }

  return (
    <section>
      <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2.5">
          <span className="grid h-8 w-8 place-items-center rounded-lg bg-accent/10 text-accent-soft">
            <Sparkles size={16} aria-hidden="true" />
          </span>
          <div>
            <h2 className="text-sm font-semibold text-slate-100">Optimization Proposals</h2>
            <p className="text-xs text-slate-500">
              Human-reviewed recommendations from structure, KPI signals and cost data.
            </p>
          </div>
        </div>
        <button className="btn-primary" onClick={onOptimize} disabled={busy || !processId}>
          <Sparkles size={16} aria-hidden="true" />
          {busy ? 'Analyzing…' : 'Run Optimizer'}
        </button>
      </div>

      {proposals.length === 0 ? (
        <div className="glass flex flex-col items-center gap-2 p-10 text-center text-sm text-slate-400">
          <span className="grid h-12 w-12 place-items-center rounded-full bg-white/[0.04] text-slate-500">
            <Lightbulb size={22} aria-hidden="true" />
          </span>
          <p className="font-medium text-slate-200">No proposals yet</p>
          <p className="max-w-md text-slate-500">
            Run the optimizer to generate advisory suggestions. Costed nodes and KPI samples improve
            the quality of ROI estimates.
          </p>
        </div>
      ) : (
        <ul className="space-y-3">
          <AnimatePresence initial={false}>
            {proposals.map((p) => (
              <motion.li
                key={p.id}
                layout
                initial={reduceMotion ? false : { opacity: 0, y: 10 }}
                animate={reduceMotion ? undefined : { opacity: 1, y: 0 }}
                exit={reduceMotion ? undefined : { opacity: 0 }}
                className="glass-strong p-4"
              >
                <div className="flex min-w-0 items-start justify-between gap-3">
                  <div className="min-w-0">
                    <p className="truncate text-sm font-semibold text-slate-100">{p.title}</p>
                    <p className="mt-1 text-xs text-slate-500">
                      Confidence{' '}
                      <span className="number text-slate-300">
                        {formatNumber(p.confidence * 100)}%
                      </span>
                    </p>
                  </div>
                  <span className={cn('chip shrink-0', STATUS_CHIP[p.status])}>{p.status}</span>
                </div>
                <p className="mt-1.5 text-sm text-slate-400">{p.rationale}</p>
                {p.estimated_savings && (
                  <div className="mt-3 inline-flex max-w-full items-center gap-2 rounded-lg border border-sev-low/20 bg-sev-low/10 px-3 py-2">
                    <TrendingUp size={15} className="shrink-0 text-sev-low" aria-hidden="true" />
                    <span className="number text-sm font-semibold text-sev-low">
                      {formatNumber(p.estimated_savings.amount)} {p.estimated_savings.currency}
                      <span className="text-[11px] font-normal text-slate-400">
                        {' '}
                        /{p.estimated_savings.period === 'annual' ? 'yr' : 'case'}
                      </span>
                    </span>
                    <span className="truncate text-[11px] text-slate-500">
                      {p.estimated_savings.basis}
                    </span>
                  </div>
                )}
                {p.expected_impact && !p.estimated_savings && (
                  <p className="mt-1.5 text-xs text-accent-soft">Expected: {p.expected_impact}</p>
                )}
                <div className="mt-3 flex flex-wrap items-center gap-2 text-[11px] text-slate-500">
                  {p.addresses_kpis.length > 0 && (
                    <span className="break-words font-mono">
                      KPIs: {p.addresses_kpis.join(', ')}
                    </span>
                  )}
                  {p.target_nodes.length > 0 && (
                    <span className="break-words font-mono">
                      Steps: {p.target_nodes.join(', ')}
                    </span>
                  )}
                </div>
                {p.status === 'proposed' && (
                  <div className="mt-4 flex gap-2">
                    <button
                      className="btn-primary"
                      disabled={deciding === p.id}
                      onClick={() => decide(p.id, true)}
                    >
                      <Check size={16} aria-hidden="true" />
                      Approve
                    </button>
                    <button
                      className="btn-ghost"
                      disabled={deciding === p.id}
                      onClick={() => decide(p.id, false)}
                    >
                      <X size={16} aria-hidden="true" />
                      Reject
                    </button>
                  </div>
                )}
              </motion.li>
            ))}
          </AnimatePresence>
        </ul>
      )}
    </section>
  );
}
