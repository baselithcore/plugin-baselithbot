import { motion } from 'framer-motion';
import {
  Check,
  Copy,
  FileText,
  Loader2,
  Pen,
  RefreshCw,
  Sparkles,
  User,
  X,
} from 'lucide-react';
import { useMemo, useState } from 'react';
import ReactMarkdown, { defaultUrlTransform } from 'react-markdown';
import rehypeHighlight from 'rehype-highlight';
import remarkGfm from 'remark-gfm';
import type { Message as Msg } from '../lib/types';
import type { Citation } from '../lib/citations';
import { prepareCitations, stripTrailingSourcesBlock } from '../lib/citations';
import { cn } from '../lib/cn';
import { useAuth } from '../contexts/AuthContext';
import { duration, ease } from '../lib/motion';
import { CitationBadge } from './CitationBadge';
import { FeedbackButtons } from './FeedbackButtons';
import { CitationWarningBanner } from './message/CitationWarningBanner';
import { SourcesFooter } from './message/SourcesFooter';
import { ThinkingPanel } from './message/ThinkingPanel';
import { Timer } from './Timer';

interface Props {
  message: Msg;
  isLast: boolean;
  onPickSource: (docId: string, anchor?: string) => void;
  onOpenSources: () => void;
  editionLabel?: string | null;
  onRegenerate?: () => void;
  onEdit?: (messageId: string, content: string) => void;
  showTrace?: boolean;
  showTimer?: boolean;
  /** prompt utente che ha prodotto questa risposta (per telemetria feedback) */
  pairedQuestion?: string;
  /** feature flag da `/api/status` — disabilita UI voto se false */
  feedbackEnabled?: boolean;
}

/**
 * react-markdown 10 azzera per default href con scheme non whitelistati
 * (cite://, wiki://). Senza override l'anchor risulta `<a href="">` e il
 * click ricarica la pagina corrente — visto come "refresh strano". Qui
 * lasciamo passare i due scheme interni e ricadiamo sul transformer
 * di default per tutto il resto (no XSS regression).
 */
function citationUrlTransform(url: string): string {
  if (url.startsWith('cite://') || url.startsWith('wiki://')) return url;
  return defaultUrlTransform(url);
}

/**
 * Rendering custom:
 * - avatar a sinistra (utente = iniziale / assistente = sparkles)
 * - markdown con gfm + syntax highlight
 * - wikilink `[[target]]` → CitationBadge numerato (superscript) se la fonte
 *   è fra quelle del backend; altrimenti chip `.wikilink` legacy
 * - footer "Fonti" numerate con verify button per-source
 * - disclaimer edizione contrattuale in coda
 */
export function ChatMessage({
  message,
  isLast,
  onPickSource,
  onOpenSources,
  editionLabel,
  onRegenerate,
  onEdit,
  showTrace = true,
  showTimer = true,
  pairedQuestion,
  feedbackEnabled = true,
}: Props) {
  const isUser = message.role === 'user';
  const { can } = useAuth();
  // Gating fonti (perm view.sources, mig 014). Quando l'utente non ce
  // l'ha: niente footer "Fonti citate", niente badge cliccabili inline,
  // niente wikilink di navigazione — la risposta resta prosa pulita
  // senza affordance verso un pannello che comunque non vedrebbe.
  const canViewSources = can('view.sources');
  const [copied, setCopied] = useState(false);
  const [editing, setEditing] = useState(false);
  const [editValue, setEditValue] = useState(message.content);

  const beginEdit = () => {
    setEditValue(message.content);
    setEditing(true);
  };
  const commitEdit = () => {
    if (!onEdit) return;
    const trimmed = editValue.trim();
    if (trimmed && trimmed !== message.content) {
      onEdit(message.id, trimmed);
    }
    setEditing(false);
  };
  const cancelEdit = () => {
    setEditing(false);
    setEditValue(message.content);
  };

  // citazioni inline numerate — stabili nell'ordine di prima comparsa.
  // Strip del blocco "Fonti:" finale (LLM lo emette, ma il SourcesFooter
  // lo rende già con titoli + rango + anchor → evita doppia citazione).
  // Solo a streaming completato per non far flickerare la lista mentre
  // i bullet entrano uno alla volta.
  const { content: preparedContent, citations } = useMemo(() => {
    if (isUser) return { content: message.content, citations: [] as Citation[] };
    const raw = message.streaming
      ? message.content
      : stripTrailingSourcesBlock(message.content);
    return prepareCitations(raw, message.sources ?? []);
  }, [isUser, message.content, message.sources, message.streaming]);

  // Sostituisce token [CIT:n] con link markdown cite://n (stesso pattern usato
  // per wiki://), così il renderer intercetta via components.a e rende badge.
  const prepared = useMemo(() => {
    if (isUser) return preparedContent;
    return preparedContent.replace(/\[CIT:(\d+)\]/g, (_m, n) => `[${n}](cite://${n})`);
  }, [isUser, preparedContent]);

  const handleCopy = async () => {
    await navigator.clipboard.writeText(message.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };

  return (
    <motion.article
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: duration.base, ease: ease.outQuart }}
      className={cn(
        'group flex gap-3.5 px-4 py-5 sm:gap-4 sm:px-8',
        !isUser && 'border-b border-[var(--color-border)]/60 last:border-b-0',
        isLast && 'pb-8',
      )}
      role="article"
      aria-label={isUser ? 'messaggio utente' : 'risposta assistente'}
    >
      <div className="shrink-0">
        <div
          className={cn(
            'grid size-8 place-items-center rounded-xl text-[11px] font-semibold',
            isUser
              ? 'border border-[var(--color-border)] bg-[var(--color-surface)] text-ink-muted'
              : 'text-white shadow-[var(--shadow-brand)]',
          )}
          style={
            isUser
              ? undefined
              : {
                  background:
                    'linear-gradient(135deg, var(--color-brand) 0%, var(--color-accent) 135%)',
                }
          }
        >
          {isUser ? <User size={14} aria-hidden /> : <Sparkles size={14} aria-hidden />}
        </div>
      </div>

      <div className="min-w-0 flex-1">
        <div className="mb-1 flex flex-wrap items-center gap-2">
          <span className="font-display text-[13px] font-bold text-ink tracking-[-0.01em]">{isUser ? 'Tu' : 'Assistente'}</span>
          {!isUser && showTimer && (
            <Timer
              startedAt={message.startedAt}
              firstTokenAt={message.firstTokenAt}
              completedAt={message.completedAt}
              streaming={message.streaming}
            />
          )}
          {/* Fallback header indicator: visible only while streaming AND
              the ThinkingPanel below isn't covering the state (no trace
              events yet, or showTrace disabled). Avoids the legacy
              duplicate-spinner UX when both rendered. */}
          {message.streaming &&
            (!showTrace || !message.trace || message.trace.length === 0) && (
              <span
                className="inline-flex items-center gap-1 text-[10px] text-[var(--color-brand)]"
                role="status"
                aria-live="polite"
              >
                <Loader2 size={10} className="animate-spin" aria-hidden /> generazione…
              </span>
            )}
        </div>

        {showTrace &&
          message.role === 'assistant' &&
          message.trace &&
          message.trace.length > 0 &&
          message.streaming && (
            <ThinkingPanel
              trace={message.trace}
              streaming={message.streaming}
              startedAt={message.startedAt}
              firstTokenAt={message.firstTokenAt}
              completedAt={message.completedAt}
            />
          )}

        <div
          className={cn('md', message.streaming && !message.content && 'text-ink-subtle')}
          aria-live={message.streaming ? 'polite' : undefined}
        >
          {isUser ? (
            editing ? (
              <div className="flex flex-col gap-2">
                <textarea
                  value={editValue}
                  onChange={(e) => setEditValue(e.target.value)}
                  onKeyDown={(e) => {
                    if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') {
                      e.preventDefault();
                      commitEdit();
                    } else if (e.key === 'Escape') {
                      e.preventDefault();
                      cancelEdit();
                    }
                  }}
                  rows={Math.min(8, Math.max(2, editValue.split('\n').length + 1))}
                  className="focus-ring w-full rounded-lg
                             bg-[var(--color-canvas-raised)] border border-[var(--color-brand-ring)]
                             px-3 py-2 text-sm resize-none"
                  aria-label="modifica messaggio"
                  autoFocus
                />
                <div className="flex items-center gap-1.5">
                  <button
                    onClick={commitEdit}
                    className="focus-ring inline-flex items-center gap-1 rounded-md
                               bg-[var(--color-brand)] text-white
                               px-2.5 py-1 text-[11px] font-medium hover:bg-[var(--color-brand-strong)]"
                  >
                    <Check size={11} /> Salva e rigenera
                    <kbd className="ml-1 rounded bg-white/15 px-1 font-mono text-[9px] leading-none">
                      ⌘↵
                    </kbd>
                  </button>
                  <button
                    onClick={cancelEdit}
                    className="focus-ring inline-flex items-center gap-1 rounded-md
                               border border-[var(--color-border)] bg-[var(--color-surface)]
                               px-2.5 py-1 text-[11px] font-medium text-ink-muted hover:text-ink"
                  >
                    <X size={11} /> Annulla
                  </button>
                </div>
              </div>
            ) : (
              <p className="whitespace-pre-wrap">{message.content}</p>
            )
          ) : message.content ? (
            <ReactMarkdown
              remarkPlugins={[remarkGfm]}
              rehypePlugins={[rehypeHighlight]}
              urlTransform={citationUrlTransform}
              components={{
                a({ href, children, ...rest }) {
                  if (href?.startsWith('cite://')) {
                    const n = Number(href.slice(7));
                    const cit = citations.find((c) => c.n === n);
                    if (cit) {
                      // Senza view.sources renderiamo un badge non-cliccabile:
                      // l'utente vede ancora il marcatore [n] (la prosa lo
                      // referenzia) ma non c'è azione → niente pannello fonti.
                      if (!canViewSources) {
                        return (
                          <span
                            className="citation-ref !cursor-default"
                            aria-label={`citazione ${cit.n}`}
                          >
                            {cit.n}
                          </span>
                        );
                      }
                      return (
                        <CitationBadge
                          citation={cit}
                          onOpen={(docId, anchor) => {
                            onPickSource(docId, anchor);
                            onOpenSources();
                          }}
                        />
                      );
                    }
                  }
                  if (href?.startsWith('wiki://')) {
                    const docId = decodeURIComponent(href.slice(7));
                    if (!canViewSources) {
                      // Niente affordance di navigazione: testo plain.
                      return <span className="font-medium">{children}</span>;
                    }
                    return (
                      <button
                        onClick={() => {
                          onPickSource(docId);
                          onOpenSources();
                        }}
                        className="wikilink focus-ring"
                        title={`apri ${docId}`}
                      >
                        <FileText size={10} />
                        {children}
                      </button>
                    );
                  }
                  return (
                    <a href={href} target="_blank" rel="noreferrer" {...rest}>
                      {children}
                    </a>
                  );
                },
              }}
            >
              {prepared}
            </ReactMarkdown>
          ) : (
            <span className="cursor-blink" />
          )}
          {message.streaming && message.content && <span className="cursor-blink" />}
        </div>

        {message.error && (
          <div
            role="alert"
            className="mt-2 flex items-start justify-between gap-2 rounded-lg border border-[var(--color-danger)]/40 bg-[var(--color-danger)]/8 px-3 py-2"
          >
            <div className="min-w-0 text-xs text-[var(--color-danger)]">
              <div className="font-semibold">Risposta interrotta</div>
              <div className="text-[11px] opacity-90">{message.error}</div>
            </div>
            {onRegenerate && (
              <button
                onClick={onRegenerate}
                className="focus-ring inline-flex shrink-0 items-center gap-1 rounded-md border border-[var(--color-danger)]/40 bg-[var(--color-canvas-raised)] px-2 py-1 text-[11px] font-medium text-[var(--color-danger)] hover:bg-[var(--color-surface)]"
              >
                <RefreshCw size={11} aria-hidden /> Riprova
              </button>
            )}
          </div>
        )}

        {/* Banner violazioni citazioni (validator backend post-generation) */}
        {!message.streaming &&
          !isUser &&
          message.citationWarning &&
          message.citationWarning.violations.length > 0 && (
            <CitationWarningBanner warning={message.citationWarning} />
          )}

        {/* Footer fonti numerate — gated da view.sources (mig 014). */}
        {!message.streaming &&
          !isUser &&
          canViewSources &&
          (citations.length > 0 || (message.sources && message.sources.length > 0)) && (
            <SourcesFooter
              citations={citations}
              extras={(message.sources ?? []).filter(
                (s) => !citations.some((c) => c.source?.document_id === s.document_id)
              )}
              onOpenSources={onOpenSources}
              onPickSource={onPickSource}
            />
          )}

        {/* Disclaimer edizione — obbligo CLAUDE.md versioning */}
        {!message.streaming && !isUser && message.content && editionLabel && (
          <p className="mt-3 text-[10.5px] text-ink-subtle italic leading-relaxed">
            I valori citati si riferiscono a <span className="font-medium">{editionLabel}</span>. Se
            il contratto dell'Assicurato ha edizione diversa, verifica i valori in Polizza o
            fornisci la data di decorrenza.
          </p>
        )}

        {/* azioni user message (edit) */}
        {isUser && !editing && onEdit && (
          <div className="mt-2 flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
            <button
              onClick={beginEdit}
              className="focus-ring inline-flex items-center gap-1 rounded-md border border-[var(--color-border)] bg-[var(--color-surface)]
                         px-2 py-1 text-[10px] font-medium text-ink-muted hover:text-ink"
              title="modifica e rigenera"
            >
              <Pen size={11} /> modifica
            </button>
          </div>
        )}

        {/* azioni (copy / rigenera / feedback) */}
        {!isUser && !message.streaming && message.content && (
          <div className="mt-3 flex items-center gap-1 flex-wrap">
            {feedbackEnabled && (
              <FeedbackButtons
                messageId={message.id}
                answer={message.content}
                question={pairedQuestion}
                sources={message.sources}
                edition={editionLabel}
              />
            )}
            <button
              onClick={handleCopy}
              className="focus-ring inline-flex items-center gap-1 rounded-md border border-[var(--color-border)] bg-[var(--color-surface)]
                         px-2 py-1 text-[10px] font-medium text-ink-muted hover:text-ink"
            >
              {copied ? <Check size={11} /> : <Copy size={11} />}
              {copied ? 'copiato' : 'copia'}
            </button>
            {onRegenerate && (
              <button
                onClick={onRegenerate}
                className="focus-ring inline-flex items-center gap-1 rounded-md border border-[var(--color-border)] bg-[var(--color-surface)]
                           px-2 py-1 text-[10px] font-medium text-ink-muted hover:text-ink"
                title="rigenera risposta"
              >
                <RefreshCw size={11} />
                rigenera
              </button>
            )}
          </div>
        )}
      </div>
    </motion.article>
  );
}
