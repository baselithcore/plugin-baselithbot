/**
 * Empty state for the knowledge-graph page when FalkorDB is up but
 * no entities have been extracted yet (fresh install, GRAPH_EXTRACT
 * disabled at ingest time, or pack just scaffolded).
 *
 * Teaches: what the graph is, how to populate it, when it appears.
 * Single dismissible hint above the CTA so users who've already seen
 * the explainer don't get repeat noise after a `rebuild`.
 */

import { motion } from 'framer-motion';
import { Network, Sparkles, Terminal } from 'lucide-react';
import { Callout } from '../ui';
import { duration, ease } from '../../lib/motion';

interface GraphEmptyStateProps {
  /** Optional refresh trigger so users can re-check after running rebuild. */
  onReload: () => void;
}

export function GraphEmptyState({ onReload }: GraphEmptyStateProps) {
  return (
    <div className="m-auto flex max-w-2xl flex-col items-center gap-5 px-6 py-10 text-center">
      <motion.div
        initial={{ opacity: 0, scale: 0.92 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: duration.slow, ease: ease.outQuart }}
        className="grid size-16 place-items-center rounded-2xl border border-[var(--color-brand-ring)] bg-[var(--color-brand-soft)] text-[var(--color-brand)]"
      >
        <Network size={28} strokeWidth={1.6} aria-hidden />
      </motion.div>

      <div className="flex flex-col gap-1">
        <h2 className="text-lg font-semibold text-ink">Il grafo è vuoto</h2>
        <p className="text-sm text-ink-muted leading-relaxed">
          Nessuna entità estratta dalle pagine wiki. Il grafo si popola
          automaticamente durante l'ingest quando l'estrazione è attiva,
          oppure manualmente da CLI sulle pagine già caricate.
        </p>
      </div>

      <Callout tone="info" title="Cos'è il knowledge graph" className="w-full text-left">
        <ul className="mt-1 list-disc space-y-1 pl-4 text-[11.5px]">
          <li>
            <strong>Entità</strong> (nodi): persone, concetti, sistemi, norme citati
            nelle pagine.
          </li>
          <li>
            <strong>Relazioni</strong> (archi): legami tipati con confidence
            <span className="mx-1 font-mono text-[10.5px]">EXTRACTED / INFERRED / AMBIGUOUS</span>.
          </li>
          <li>
            <strong>Community</strong>: cluster di entità densamente collegate —
            colorate uniformemente sulla canvas.
          </li>
          <li>
            <strong>Surprising connections</strong>: archi ad alta confidence fra
            community diverse — i ponti concettuali più informativi.
          </li>
        </ul>
      </Callout>

      <Callout tone="neutral" title="Estrai entità dalle pagine" icon={Terminal} className="w-full text-left">
        <p>
          Esegui dal terminale, una volta sola — è idempotente e riusa il
          modello LLM configurato per l'ingest.
        </p>
        <pre className="mt-2 overflow-x-auto rounded-md border border-[var(--color-border)] bg-[var(--color-canvas)] px-2.5 py-1.5 font-mono text-[11px] text-ink">
          wiki-wl graph rebuild
        </pre>
        <p className="mt-2 text-[10.5px]">
          Per l'estrazione automatica al prossimo ingest, imposta{' '}
          <code className="rounded bg-[var(--color-surface)] px-1 font-mono text-[10.5px]">
            GRAPH_EXTRACT_ENABLED=true
          </code>{' '}
          in <code className="font-mono text-[10.5px]">.env</code>.
        </p>
      </Callout>

      <button
        type="button"
        onClick={onReload}
        className="focus-ring inline-flex items-center gap-1.5 rounded-lg bg-[var(--color-brand)] px-3 py-1.5 text-xs font-semibold text-white hover:bg-[var(--color-brand-strong)]"
      >
        <Sparkles size={12} aria-hidden /> Ricarica grafo
      </button>
    </div>
  );
}
