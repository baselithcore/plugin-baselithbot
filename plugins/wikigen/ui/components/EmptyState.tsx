import { motion } from 'framer-motion';
import {
  AlertCircle,
  ArrowUpRight,
  BookOpen,
  Building2,
  ClipboardList,
  FileSearch,
  Gavel,
  Loader2,
  type LucideIcon,
  Network,
  Scale,
  ShieldCheck,
  Sparkles,
  Upload,
  Wallet,
} from 'lucide-react';
import { useCallback, useEffect, useState } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { useDomain, type SuggestedQuestion } from '../contexts/DomainContext';
import { fetchJobs, fetchPendingRaw, ingestRawFromDisk } from '../lib/api';
import { cn } from '../lib/cn';
import { duration, ease } from '../lib/motion';
import { toast } from 'sonner';
import { Hint } from './ui';

const ICONS: Record<string, LucideIcon> = {
  Sparkles,
  Scale,
  Building2,
  ShieldCheck,
  ClipboardList,
  Wallet,
  FileSearch,
  Gavel,
  BookOpen,
  Network,
};

function iconFor(s: SuggestedQuestion): LucideIcon {
  if (s.icon && ICONS[s.icon]) return ICONS[s.icon];
  // category fallback mapping
  switch (s.category) {
    case 'copertura':
      return Building2;
    case 'esclusioni':
      return ShieldCheck;
    case 'sinistri':
      return ClipboardList;
    case 'calcoli':
      return Wallet;
    case 'confronti':
      return FileSearch;
    case 'normativa':
      return Gavel;
    default:
      return BookOpen;
  }
}

// Knowledge-graph constellation — the Grafiphy signature motif. Vertices
// (cobalt + coral) wired by faint edges. Small "packet" circles ride each
// edge end-to-end via SVG <animateMotion>, evoking data flowing through the
// graph. Decorative only (aria-hidden); honoured by prefers-reduced-motion.
const NODES = [
  { x: 8, y: 18, r: 1.3, accent: false, delay: 0 },
  { x: 18, y: 70, r: 0.9, accent: true, delay: 1.1 },
  { x: 32, y: 12, r: 0.85, accent: false, delay: 0.6 },
  { x: 62, y: 82, r: 1.15, accent: false, delay: 1.6 },
  { x: 78, y: 22, r: 1, accent: true, delay: 0.3 },
  { x: 92, y: 68, r: 1.25, accent: false, delay: 0.9 },
  { x: 92, y: 14, r: 0.8, accent: true, delay: 2 },
] as const;
const EDGES = [
  [0, 2],
  [0, 6],
  [2, 4],
  [6, 1],
  [6, 3],
  [4, 5],
  [3, 5],
  [4, 6],
] as const;

function GraphConstellation() {
  const mask =
    'radial-gradient(ellipse 74% 66% at 50% 42%, black 0%, rgba(0,0,0,0.82) 58%, transparent 100%)';
  return (
    <svg
      aria-hidden
      className="graph-constellation pointer-events-none absolute inset-0 h-full w-full"
      viewBox="0 0 100 90"
      preserveAspectRatio="xMidYMid slice"
      style={{ WebkitMaskImage: mask, maskImage: mask }}
    >
      <defs>
        {EDGES.map(([a, b], i) => (
          <path
            key={`p-${i}`}
            id={`edge-path-${i}`}
            d={`M ${NODES[a].x} ${NODES[a].y} L ${NODES[b].x} ${NODES[b].y}`}
            fill="none"
          />
        ))}
      </defs>
      <g
        stroke="var(--color-brand)"
        strokeOpacity="var(--hero-edge-opacity)"
        strokeWidth="var(--hero-edge-width)"
      >
        {EDGES.map(([a, b], i) => (
          <line key={i} x1={NODES[a].x} y1={NODES[a].y} x2={NODES[b].x} y2={NODES[b].y} />
        ))}
      </g>
      <g>
        {NODES.map((node, i) => (
          <circle
            key={`n-${i}`}
            cx={node.x}
            cy={node.y}
            r={node.r}
            fill={node.accent ? 'var(--color-accent)' : 'var(--color-brand)'}
            fillOpacity="var(--hero-node-opacity)"
          >
            <animate
              attributeName="r"
              values={`${node.r};${node.r * 1.55};${node.r}`}
              dur="4.8s"
              begin={`${node.delay}s`}
              repeatCount="indefinite"
            />
            <animate
              attributeName="fill-opacity"
              values="var(--hero-node-opacity);var(--hero-node-peak-opacity);var(--hero-node-opacity)"
              dur="4.8s"
              begin={`${node.delay}s`}
              repeatCount="indefinite"
            />
          </circle>
        ))}
      </g>
      {/* Traveling packets — circles riding each edge end-to-end */}
      {EDGES.map(([a, b], i) => {
        const accent = NODES[a].accent || NODES[b].accent;
        return (
          <circle
            key={`t-${i}`}
            r={0.75}
            fill={accent ? 'var(--color-accent)' : 'var(--color-brand)'}
            fillOpacity="var(--hero-packet-opacity)"
          >
            <animateMotion
              dur={`${5 + (i % 4) * 0.9}s`}
              begin={`${i * 0.55}s`}
              repeatCount="indefinite"
              rotate="auto"
            >
              <mpath href={`#edge-path-${i}`} />
            </animateMotion>
          </circle>
        );
      })}
    </svg>
  );
}

interface Props {
  onPick: (prompt: string) => void;
}

export function EmptyState({ onPick }: Props) {
  const { branding } = useDomain();
  const { can } = useAuth();
  const ui = branding?.ui;
  const heroQuestion = ui?.hero_question || 'Cosa vuoi sapere';
  const heroHighlight = ui?.hero_highlight || 'dalla tua Wiki?';
  const heroPill = ui?.hero_pill || 'GraphRAG · retrieval su grafo · anchor-first';
  const HeroPillIcon = (ui?.hero_pill_icon && ICONS[ui.hero_pill_icon]) || Network;
  const description =
    ui?.empty_state ||
    'Domande ancorate alle fonti caricate. Ogni risposta cita verbatim.';
  const disclaimer = ui?.disclaimer || '';
  const suggestions = ui?.suggested_questions ?? [];

  // Pending-ingest detection: PDFs in raw/ that don't yet have a wiki
  // source page. Surfaces a CTA banner + tracks running ingest jobs so
  // first-run users see immediate feedback after the wizard's "Documenti"
  // step.
  const [pending, setPending] = useState<{ count: number; names: string[] } | null>(null);
  const [running, setRunning] = useState(0);
  const [ingestStarting, setIngestStarting] = useState(false);

  const refreshPending = useCallback(async () => {
    try {
      const [pendR, jobsR] = await Promise.all([fetchPendingRaw(), fetchJobs(20)]);
      setPending({
        count: pendR.count,
        names: pendR.files.map((f) => f.name),
      });
      setRunning(
        jobsR.jobs.filter((j) => j.status === 'queued' || j.status === 'running').length
      );
    } catch {
      setPending(null);
    }
  }, []);

  useEffect(() => {
    refreshPending();
    // Poll while there's pending or running activity.
    const id = window.setInterval(refreshPending, 4000);
    return () => window.clearInterval(id);
  }, [refreshPending]);

  const startBulkIngest = async () => {
    setIngestStarting(true);
    try {
      const r = await ingestRawFromDisk(null);
      toast.success(`Ingestion avviata su ${r.started} file. Apri ⌘U per vedere i progress.`);
      setTimeout(refreshPending, 1500);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Avvio fallito');
    } finally {
      setIngestStarting(false);
    }
  };

  const showIngestBanner = pending !== null && (pending.count > 0 || running > 0);

  return (
    <div className="mesh-hero grain relative flex flex-1 flex-col overflow-hidden">
      <GraphConstellation />
      <div className="relative z-10 flex-1 overflow-y-auto">
        <div className="flex min-h-full flex-col items-center justify-center px-5 py-10 sm:px-6">
      {showIngestBanner && (
        <motion.div
          initial={{ opacity: 0, y: -8 }}
          animate={{ opacity: 1, y: 0 }}
          className={cn(
            'relative z-10 mb-6 w-full max-w-3xl rounded-xl border px-4 py-3 flex items-center justify-between gap-3 shadow-[var(--shadow-md)]',
            running > 0
              ? 'border-[var(--color-brand-ring)] bg-[var(--color-brand-soft)]'
              : 'border-amber-500/40 bg-amber-500/5'
          )}
          role="status"
        >
          <div className="flex items-center gap-2.5 min-w-0">
            {running > 0 ? (
              <Loader2
                size={16}
                className="text-[var(--color-brand)] shrink-0 animate-spin"
                aria-hidden
              />
            ) : (
              <AlertCircle
                size={16}
                className="text-amber-600 dark:text-amber-400 shrink-0"
                aria-hidden
              />
            )}
            <div className="min-w-0">
              <div className="text-[12.5px] font-semibold">
                {running > 0
                  ? `Elaborazione in corso · ${running} ${running === 1 ? 'documento' : 'documenti'}`
                  : `${pending!.count} ${pending!.count === 1 ? 'documento' : 'documenti'} in attesa di elaborazione`}
              </div>
              <div className="truncate text-[11px] text-ink-muted">
                {running > 0
                  ? 'Le pagine generate compariranno qui appena pronte.'
                  : 'Avvia l\'elaborazione per renderli consultabili dalla chat.'}
              </div>
            </div>
          </div>
          {pending!.count > 0 && (
            <button
              onClick={startBulkIngest}
              disabled={ingestStarting}
              className="focus-ring inline-flex shrink-0 items-center gap-1.5 rounded-lg
                         bg-[var(--color-brand)] px-3 py-1.5 text-xs font-semibold text-white
                         hover:bg-[var(--color-brand-strong)] disabled:cursor-not-allowed disabled:opacity-40"
            >
              {ingestStarting ? (
                <Loader2 size={12} className="animate-spin" aria-hidden />
              ) : (
                <Upload size={12} aria-hidden />
              )}
              {ingestStarting ? 'Avvio…' : 'Elabora tutti'}
            </button>
          )}
        </motion.div>
      )}

      <div className="relative z-10 flex w-full max-w-5xl flex-col items-center text-center">
        <motion.div
          initial={{ opacity: 0, y: 12, scale: 0.96 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          transition={{ duration: duration.slow, ease: ease.outExpo }}
          className="mb-4 inline-flex items-center gap-1.5 rounded-full border border-[var(--color-brand-ring)]
                     bg-[var(--color-canvas-raised)]/78 px-3 py-1.5 text-[10px] font-semibold uppercase
                     tracking-[0.1em] text-[var(--color-brand-contrast)] shadow-[var(--shadow-xs)] backdrop-blur"
        >
          <HeroPillIcon size={12} /> {heroPill}
        </motion.div>

        <motion.h1
          initial={{ opacity: 0, y: 18 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.06, ease: ease.outExpo }}
          className="font-display text-[2.55rem] font-extrabold leading-[0.98] text-ink sm:text-6xl lg:text-[4.5rem]"
        >
          {heroQuestion}{' '}
          <span
            className="relative inline-block bg-clip-text text-transparent"
            style={{
              backgroundImage:
                'linear-gradient(100deg, var(--color-brand-strong) 0%, var(--color-brand) 48%, var(--color-accent) 100%)',
            }}
          >
            {heroHighlight}
            {/* Hand-drawn underline — gradient stroke matching the wordmark sweep */}
            <svg
              aria-hidden
              viewBox="0 0 200 12"
              preserveAspectRatio="none"
              className="absolute -bottom-1 left-0 h-[0.32em] w-full overflow-visible"
            >
              <defs>
                <linearGradient id="hero-underline" x1="0" y1="0" x2="1" y2="0">
                  <stop offset="0%" stopColor="var(--color-brand-strong)" />
                  <stop offset="50%" stopColor="var(--color-brand)" />
                  <stop offset="100%" stopColor="var(--color-accent)" />
                </linearGradient>
              </defs>
              <motion.path
                d="M2 8 C 50 3, 150 3, 198 7"
                fill="none"
                stroke="url(#hero-underline)"
                strokeWidth={3}
                strokeLinecap="round"
                initial={{ pathLength: 0, opacity: 0 }}
                animate={{ pathLength: 1, opacity: 0.95 }}
                transition={{ duration: 0.7, delay: 0.45, ease: ease.outExpo }}
              />
            </svg>
          </span>
        </motion.h1>

        <motion.p
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: duration.slow, delay: 0.18, ease: ease.outQuart }}
          className="mt-5 max-w-2xl text-[15px] leading-relaxed text-ink-muted sm:text-base"
        >
          {description}
        </motion.p>

        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: duration.slow, delay: 0.26, ease: ease.outQuart }}
          className="w-full max-w-3xl"
        >
          <Hint
            id="empty.first_session"
            tone="neutral"
            className="mt-6 w-full text-left"
            title="Primi passi"
          >
            <ul className="flex flex-col gap-1 text-[11.5px]">
              {/* Mostra solo le scorciatoie effettivamente operative per
                  l'utente: filtra per permesso lato render così l'hint non
                  promette qualcosa che il keybinding gated in App.tsx
                  intercetterebbe come no-op. */}
              <li>
                {can('conversation.write') && (
                  <>
                    <kbd className="font-mono text-[10px]">⌘K</kbd> nuova conversazione
                  </>
                )}
                {can('conversation.write') && can('ingest.run') && ' · '}
                {can('ingest.run') && (
                  <>
                    <kbd className="font-mono text-[10px]">⌘U</kbd> carica documento
                  </>
                )}
                {(can('conversation.write') || can('ingest.run')) && can('view.help') && ' · '}
                {can('view.help') && (
                  <>
                    <kbd className="font-mono text-[10px]">?</kbd> tutte le scorciatoie
                  </>
                )}
              </li>
              <li>
                Scegli una domanda qui sotto, oppure scrivi liberamente.
                Le risposte citano sempre le fonti.
              </li>
              <li>
                Il contesto viene espanso automaticamente seguendo le
                relazioni del knowledge graph — utile per domande
                comparative o trasversali.
              </li>
            </ul>
          </Hint>
        </motion.div>

        {suggestions.length > 0 && (
          <div className="mt-8 grid w-full grid-cols-1 gap-3 sm:grid-cols-2">
            {suggestions.map((s, idx) => {
              const Icon = iconFor(s);
              return (
                <motion.button
                  key={`${s.category ?? 'q'}-${s.label}-${idx}`}
                  type="button"
                  onClick={() => onPick(s.prompt)}
                  initial={{ opacity: 0, y: 14 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.34 + 0.07 * idx, duration: duration.slow, ease: ease.outExpo }}
                  whileHover={{ y: -3 }}
                  whileTap={{ scale: 0.985 }}
                  className={cn(
                    'group focus-ring relative overflow-hidden rounded-xl p-4 text-left',
                    'border border-[var(--color-border)] bg-[var(--color-canvas-raised)]/86 backdrop-blur',
                    'hover:border-[var(--color-brand-ring)] hover:shadow-[var(--shadow-glow)]',
                    'transition-[border-color,box-shadow,transform]'
                  )}
                >
                  {/* coral edge that wipes in on hover — energetic affordance */}
                  <span
                    aria-hidden
                    className="absolute inset-y-0 left-0 w-[3px] bg-[var(--color-accent)]
                               scale-y-0 group-hover:scale-y-100 origin-top
                               transition-transform duration-[var(--duration-base)]"
                  />
                  <div className="flex items-start gap-3">
                    <div
                      className="grid size-10 shrink-0 place-items-center rounded-lg
                                 bg-[var(--color-brand-soft)] text-[var(--color-brand)]
                                 group-hover:bg-[var(--color-brand)] group-hover:text-white
                                 group-hover:shadow-[var(--shadow-brand)]
                                 transition-[background-color,color,box-shadow]"
                    >
                      <Icon size={18} strokeWidth={2.2} />
                    </div>
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center justify-between gap-2">
                        <div className="flex items-center gap-1.5 min-w-0">
                          {s.category && (
                            <span
                              className="chip !px-1.5 !py-0 !text-[9px] !bg-[var(--color-surface)] !text-ink-subtle !border-[var(--color-border)]
                                         uppercase"
                            >
                              {s.category}
                            </span>
                          )}
                          <div className="font-display truncate text-[14px] font-bold tracking-[-0.01em] text-ink">
                            {s.label}
                          </div>
                        </div>
                        <ArrowUpRight
                          size={15}
                          className="shrink-0 text-[var(--color-accent)] opacity-0 -translate-x-1 -translate-y-0.5
                                     group-hover:opacity-100 group-hover:translate-x-0 group-hover:translate-y-0
                                     transition-all"
                        />
                      </div>
                      {s.hint && (
                        <div className="mt-1 text-[10.5px] font-medium uppercase tracking-wide text-ink-subtle">
                          {s.hint}
                        </div>
                      )}
                      <div className="mt-2 line-clamp-2 text-xs leading-relaxed text-ink-muted">
                        {s.prompt}
                      </div>
                    </div>
                  </div>
                </motion.button>
              );
            })}
          </div>
        )}

        {disclaimer && (
          <p className="mt-7 text-[10.5px] text-ink-subtle leading-relaxed max-w-lg relative z-10">
            {disclaimer}
          </p>
        )}
      </div>
        </div>
      </div>
    </div>
  );
}
