import { useEffect, useMemo, useRef, useState, type KeyboardEvent } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  AlertTriangle,
  CornerDownLeft,
  FileText,
  HeartPulse,
  Send,
  Stethoscope,
} from 'lucide-react';
import clsx from 'clsx';
import type { ChatMessage } from '../lib/types';
import { useReducedMotion } from '../hooks/useReducedMotion';

interface Props {
  messages: ChatMessage[];
  pending: boolean;
  progress: number;
  onSend: (text: string) => Promise<void>;
  onFinalize: () => Promise<void>;
  canFinalize: boolean;
}

export function ChatPanel({ messages, pending, progress, onSend, onFinalize, canFinalize }: Props) {
  const [value, setValue] = useState('');
  const endRef = useRef<HTMLDivElement | null>(null);
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);
  const reduceMotion = useReducedMotion();

  useEffect(() => {
    endRef.current?.scrollIntoView({
      behavior: reduceMotion ? 'auto' : 'smooth',
    });
  }, [messages, reduceMotion]);

  const grouped = useMemo(() => groupByDay(messages), [messages]);

  const submit = async () => {
    const trimmed = value.trim();
    if (!trimmed || pending) return;
    setValue('');
    await onSend(trimmed);
    textareaRef.current?.focus();
  };

  const handleKey = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if ((e.key === 'Enter' && (e.metaKey || e.ctrlKey)) || (e.key === 'Enter' && !e.shiftKey)) {
      e.preventDefault();
      void submit();
    }
  };

  return (
    <section
      className="surface-strong relative flex h-full flex-col overflow-hidden"
      aria-label="Colloquio anamnestico"
    >
      <ProgressBar value={progress} />
      <header className="flex items-center justify-between border-b border-ink-200/70 bg-white/40 px-6 py-4 dark:border-ink-700/60 dark:bg-surface-dark-raised/60">
        <div className="flex items-center gap-3">
          <span className="grid h-10 w-10 place-items-center rounded-xl bg-accent-50 text-accent-700 ring-1 ring-accent-200/80 dark:bg-accent-800/30 dark:text-accent-200 dark:ring-accent-700/60">
            <HeartPulse className="h-4 w-4" aria-hidden />
          </span>
          <div className="leading-tight">
            <h2 className="font-display text-base font-semibold tracking-tight">
              Colloquio empatico
            </h2>
            <p className="text-xs text-ink-400">
              Slot-filling guidato · nessuna diagnosi al paziente
            </p>
          </div>
        </div>
        <ProgressReadout value={progress} />
      </header>

      <div
        className="scroll-fade flex-1 overflow-y-auto px-6 py-6"
        role="log"
        aria-live="polite"
        aria-relevant="additions"
      >
        {grouped.map((group) => (
          <DayGroup key={group.day} day={group.day}>
            <AnimatePresence initial={false}>
              {group.items.map((m) => (
                <motion.div
                  key={m.id}
                  layout
                  initial={reduceMotion ? { opacity: 1 } : { opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0 }}
                  transition={{ duration: 0.22, ease: [0.16, 1, 0.3, 1] }}
                  className={clsx(
                    'mb-3 flex items-end gap-2',
                    m.role === 'patient' ? 'justify-end' : 'justify-start'
                  )}
                >
                  {m.role !== 'patient' && <AgentAvatar escalate={!!m.meta?.escalate} />}
                  <Bubble message={m} />
                  {m.role === 'patient' && <PatientAvatar />}
                </motion.div>
              ))}
            </AnimatePresence>
          </DayGroup>
        ))}
        {pending && <Typing />}
        <div ref={endRef} />
      </div>

      <footer className="border-t border-ink-200/70 bg-white/40 px-4 pb-4 pt-3 dark:border-ink-700/60 dark:bg-surface-dark-raised/60">
        <div className="flex items-end gap-2">
          <div className="relative flex-1">
            <textarea
              ref={textareaRef}
              value={value}
              onChange={(e) => setValue(e.target.value)}
              onKeyDown={handleKey}
              rows={2}
              placeholder="Descriva i sintomi al paziente…"
              aria-label="Messaggio paziente"
              className="input resize-none pr-24"
              disabled={pending}
            />
            <div className="pointer-events-none absolute bottom-2.5 right-3 hidden items-center gap-1 text-2xs text-ink-400 sm:flex">
              <span className="kbd">⏎</span>
              <span>invia</span>
              <span className="mx-1">·</span>
              <span className="kbd">⇧⏎</span>
              <span>a capo</span>
            </div>
          </div>
          <div className="flex flex-col gap-2">
            <button
              type="button"
              onClick={() => void submit()}
              disabled={pending || !value.trim()}
              className="btn-primary"
              aria-label="Invia messaggio"
            >
              <Send className="h-4 w-4" aria-hidden />
              <span className="hidden sm:inline">Invia</span>
            </button>
            <button
              type="button"
              onClick={() => void onFinalize()}
              disabled={!canFinalize || pending}
              className="btn-secondary"
              aria-label="Genera report di triage"
            >
              <FileText className="h-4 w-4" aria-hidden />
              <span className="hidden sm:inline">Report</span>
            </button>
          </div>
        </div>
        <p className="mt-3 flex items-center gap-1.5 text-2xs text-ink-400">
          <CornerDownLeft className="h-3 w-3" aria-hidden />
          Le risposte assistono il medico. Nessuna diagnosi definitiva è emessa dall'agente.
        </p>
      </footer>
    </section>
  );
}

function ProgressBar({ value }: { value: number }) {
  const pct = Math.max(0, Math.min(1, value));
  return (
    <div
      className="absolute left-0 right-0 top-0 z-10 h-0.5 bg-ink-100 dark:bg-ink-700/60"
      aria-hidden
    >
      <motion.div
        className="h-full bg-gradient-to-r from-accent-500 to-accent-700"
        initial={false}
        animate={{ width: `${pct * 100}%` }}
        transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
      />
    </div>
  );
}

function ProgressReadout({ value }: { value: number }) {
  const pct = Math.round(Math.max(0, Math.min(1, value)) * 100);
  return (
    <div className="flex items-center gap-2">
      <span className="section-title">Completamento</span>
      <span className="num font-display text-lg font-semibold tracking-tight">
        {pct}
        <span className="text-sm font-medium text-ink-400">%</span>
      </span>
    </div>
  );
}

function DayGroup({ day, children }: { day: string; children: React.ReactNode }) {
  return (
    <div>
      <div className="my-4 flex items-center gap-3">
        <span className="h-px flex-1 bg-ink-200/60 dark:bg-ink-700/40" />
        <span className="pill">{day}</span>
        <span className="h-px flex-1 bg-ink-200/60 dark:bg-ink-700/40" />
      </div>
      {children}
    </div>
  );
}

function Bubble({ message }: { message: ChatMessage }) {
  const isPatient = message.role === 'patient';
  const escalate = message.meta?.escalate;
  return (
    <div
      className={clsx(
        'group relative max-w-[78%] rounded-2xl px-4 py-3 text-sm leading-relaxed shadow-e1',
        isPatient
          ? 'rounded-br-sm bg-accent-600 text-white'
          : escalate
            ? 'rounded-bl-sm border border-triage-red/40 bg-triage-red-soft text-triage-red-ink dark:bg-triage-red-soft/20 dark:text-triage-red'
            : 'rounded-bl-sm bg-white text-ink-800 ring-1 ring-ink-200/70 dark:bg-surface-dark-raised dark:text-ink-100 dark:ring-ink-700/60'
      )}
    >
      {escalate && (
        <div className="mb-2 flex items-center gap-2 text-triage-red">
          <AlertTriangle className="h-4 w-4" aria-hidden />
          <span className="text-2xs font-semibold uppercase tracking-[0.14em]">
            Red flag · escalation
          </span>
        </div>
      )}
      <p className="whitespace-pre-wrap">{message.text}</p>
      {message.meta?.target_slot && !escalate && (
        <div className="mt-2 flex flex-wrap items-center gap-1.5">
          <span className="pill bg-white/80 text-ink-500 dark:bg-ink-50/10 dark:text-ink-200">
            {message.meta.target_slot}
          </span>
          {message.meta.tone && <span className="pill-accent">{message.meta.tone}</span>}
        </div>
      )}
      <span
        className="absolute -bottom-5 right-1 hidden text-2xs text-ink-400 num group-hover:block"
        aria-hidden
      >
        {formatTime(message.timestamp)}
      </span>
    </div>
  );
}

function AgentAvatar({ escalate }: { escalate: boolean }) {
  return (
    <span
      className={clsx(
        'grid h-8 w-8 shrink-0 place-items-center rounded-full ring-1',
        escalate
          ? 'bg-triage-red-soft text-triage-red ring-triage-red/30'
          : 'bg-accent-50 text-accent-700 ring-accent-200/80 dark:bg-accent-800/30 dark:text-accent-200 dark:ring-accent-700/60'
      )}
      aria-hidden
    >
      <Stethoscope className="h-3.5 w-3.5" />
    </span>
  );
}

function PatientAvatar() {
  return (
    <span
      className="grid h-8 w-8 shrink-0 place-items-center rounded-full bg-ink-100 text-ink-500 ring-1 ring-ink-200/70 dark:bg-ink-700/40 dark:text-ink-200 dark:ring-ink-700/60"
      aria-hidden
    >
      <span className="text-2xs font-semibold">P</span>
    </span>
  );
}

function Typing() {
  return (
    <div className="mb-3 flex items-end gap-2" aria-live="polite">
      <AgentAvatar escalate={false} />
      <div className="rounded-2xl rounded-bl-sm bg-white px-4 py-3 shadow-e1 ring-1 ring-ink-200/70 dark:bg-surface-dark-raised dark:ring-ink-700/60">
        <div className="flex items-center gap-1.5">
          <Dot delay={0} />
          <Dot delay={140} />
          <Dot delay={280} />
        </div>
      </div>
    </div>
  );
}

function Dot({ delay }: { delay: number }) {
  return (
    <span
      className="block h-1.5 w-1.5 animate-bounce rounded-full bg-accent-500"
      style={{ animationDelay: `${delay}ms` }}
    />
  );
}

function groupByDay(messages: ChatMessage[]): { day: string; items: ChatMessage[] }[] {
  const out: { day: string; items: ChatMessage[] }[] = [];
  let last: string | null = null;
  for (const m of messages) {
    const d = new Date(m.timestamp);
    const day = d.toLocaleDateString('it-IT', {
      day: '2-digit',
      month: 'long',
      year: 'numeric',
    });
    if (day !== last) {
      out.push({ day, items: [] });
      last = day;
    }
    out[out.length - 1]!.items.push(m);
  }
  return out;
}

function formatTime(iso: string): string {
  try {
    return new Date(iso).toLocaleTimeString('it-IT', {
      hour: '2-digit',
      minute: '2-digit',
    });
  } catch {
    return '';
  }
}
