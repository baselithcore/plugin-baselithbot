import { useEffect, useState } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { Check, ChevronDown, ChevronUp, ListChecks, X } from 'lucide-react';
import { useAppStore, type ChecklistTaskId } from '../../store/app.js';
import { TOURS } from './tours/index.js';

interface Task {
  id: ChecklistTaskId;
  title: string;
  hint: string;
  action?: () => void;
  actionLabel?: string;
}

export function OnboardingChecklist() {
  const dismissed = useAppStore((s) => s.checklistDismissed);
  const done = useAppStore((s) => s.checklistDone);
  const dismiss = useAppStore((s) => s.dismissChecklist);
  const markDone = useAppStore((s) => s.markChecklistDone);
  const startTour = useAppStore((s) => s.startTour);
  const setCommandOpen = useAppStore((s) => s.setCommandOpen);
  const activeConnId = useAppStore((s) => s.activeConnectionId);
  const lastResponse = useAppStore((s) => s.lastResponse);
  const detailSelection = useAppStore((s) => s.detailSelection);
  const toursCompleted = useAppStore((s) => s.toursCompleted);
  const commandOpen = useAppStore((s) => s.commandOpen);
  const activeTour = useAppStore((s) => s.activeTour);

  const [expanded, setExpanded] = useState(true);

  // Auto-detect completion based on observed app state so the checklist
  // advances passively as the user works, not only when they click "Start".
  useEffect(() => {
    if (activeConnId && !done.includes('connect')) markDone('connect');
  }, [activeConnId, done, markDone]);
  useEffect(() => {
    if (lastResponse && !done.includes('ask-question')) markDone('ask-question');
  }, [lastResponse, done, markDone]);
  useEffect(() => {
    if (detailSelection && !done.includes('open-detail')) markDone('open-detail');
  }, [detailSelection, done, markDone]);
  useEffect(() => {
    if (commandOpen && !done.includes('use-command-palette')) markDone('use-command-palette');
  }, [commandOpen, done, markDone]);
  // Completing a focused tour counts as completing its checklist task — the
  // user has clearly walked through the relevant area.
  useEffect(() => {
    if (toursCompleted.includes('graph') && !done.includes('explore-schema')) {
      markDone('explore-schema');
    }
    if (toursCompleted.includes('connections') && !done.includes('connect')) {
      markDone('connect');
    }
    if (toursCompleted.includes('nl2sql') && !done.includes('ask-question')) {
      markDone('ask-question');
    }
  }, [toursCompleted, done, markDone]);

  const tasks: Task[] = [
    {
      id: 'connect',
      title: 'Connect to a database',
      hint: 'Pick a shared connection or add a new one from the left panel.',
      action: () => startTour('connections'),
      actionLabel: 'Tour',
    },
    {
      id: 'explore-schema',
      title: 'Explore the schema graph',
      hint: 'Pan, zoom, and find a table that interests you.',
      action: () => startTour('graph'),
      actionLabel: 'Tour',
    },
    {
      id: 'open-detail',
      title: 'Inspect a table',
      hint: 'Click a node to open its detail drawer with columns and sample rows.',
    },
    {
      id: 'ask-question',
      title: 'Ask a question in natural language',
      hint: 'Use the right panel — try one of the suggestions to start.',
      action: () => startTour('nl2sql'),
      actionLabel: 'Tour',
    },
    {
      id: 'use-command-palette',
      title: 'Open the command palette',
      hint: 'Press ⌘K to jump anywhere in the app.',
      action: () => {
        setCommandOpen(true);
        markDone('use-command-palette');
      },
      actionLabel: 'Open',
    },
  ];

  const completedCount = tasks.filter((t) => done.includes(t.id)).length;
  const total = tasks.length;
  const allDone = completedCount === total;

  if (dismissed || allDone || activeTour) return null;

  const tourTitles = TOURS;
  void tourTitles;

  return (
    <motion.div
      initial={{ opacity: 0, y: 12, scale: 0.96 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      exit={{ opacity: 0, y: 12 }}
      transition={{ duration: 0.28, ease: [0.22, 1, 0.36, 1] }}
      className="fixed bottom-12 right-4 z-40 w-80 rounded-xl border shadow-2xl"
      style={{
        background: 'rgb(var(--surface-elevated))',
        borderColor: 'rgb(var(--border))',
        color: 'rgb(var(--text))',
      }}
      role="region"
      aria-label="Getting started checklist"
    >
      <button
        type="button"
        onClick={() => setExpanded((v) => !v)}
        className="w-full flex items-center justify-between gap-2 px-3.5 py-2.5 text-left"
        aria-expanded={expanded}
      >
        <span className="flex items-center gap-2 min-w-0">
          <ListChecks className="w-3.5 h-3.5 text-accent shrink-0" />
          <span className="text-[13px] font-semibold">Getting started</span>
          <span className="chip h-5 px-1.5 text-[10px] font-mono">
            {completedCount}/{total}
          </span>
        </span>
        <span className="flex items-center gap-0.5">
          <span
            role="button"
            tabIndex={0}
            aria-label="Dismiss checklist"
            title="Dismiss"
            onClick={(e) => {
              e.stopPropagation();
              dismiss();
            }}
            onKeyDown={(e) => {
              if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                e.stopPropagation();
                dismiss();
              }
            }}
            className="btn-icon w-6 h-6"
          >
            <X className="w-3 h-3" />
          </span>
          {expanded ? (
            <ChevronDown className="w-3.5 h-3.5 text-text-muted" />
          ) : (
            <ChevronUp className="w-3.5 h-3.5 text-text-muted" />
          )}
        </span>
      </button>
      <div
        className="h-0.5 mx-3.5 rounded-full overflow-hidden"
        style={{ background: 'rgb(var(--border-subtle))' }}
        aria-hidden
      >
        <motion.div
          className="h-full rounded-full"
          style={{ background: 'rgb(var(--accent))' }}
          animate={{ width: `${(completedCount / total) * 100}%` }}
          transition={{ duration: 0.35 }}
        />
      </div>
      <AnimatePresence initial={false}>
        {expanded && (
          <motion.ul
            key="tasks"
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="overflow-hidden p-2 flex flex-col gap-1"
          >
            {tasks.map((task) => {
              const isDone = done.includes(task.id);
              return (
                <li
                  key={task.id}
                  className="flex items-start gap-2 px-2 py-1.5 rounded-md"
                  style={{
                    background: isDone ? 'rgb(var(--accent) / 0.08)' : 'transparent',
                  }}
                >
                  <span
                    aria-hidden
                    className="mt-0.5 w-4 h-4 rounded-full flex items-center justify-center shrink-0 border"
                    style={{
                      background: isDone ? 'rgb(var(--accent))' : 'transparent',
                      borderColor: isDone ? 'rgb(var(--accent))' : 'rgb(var(--border))',
                    }}
                  >
                    {isDone && (
                      <Check className="w-3 h-3" style={{ color: 'rgb(var(--accent-fg))' }} />
                    )}
                  </span>
                  <div className="flex-1 min-w-0">
                    <div
                      className="text-[12.5px] font-medium leading-tight"
                      style={{
                        color: isDone ? 'rgb(var(--text-muted))' : 'rgb(var(--text))',
                        textDecoration: isDone ? 'line-through' : 'none',
                      }}
                    >
                      {task.title}
                    </div>
                    {!isDone && (
                      <div
                        className="text-[11px] mt-0.5 leading-snug"
                        style={{ color: 'rgb(var(--text-dim))' }}
                      >
                        {task.hint}
                      </div>
                    )}
                  </div>
                  {!isDone && task.action && (
                    <button
                      onClick={task.action}
                      className="text-[11px] px-2 py-0.5 rounded-md hover:bg-surface-2/65 transition-colors shrink-0"
                      style={{
                        color: 'rgb(var(--accent))',
                        border: '1px solid rgb(var(--accent) / 0.35)',
                      }}
                    >
                      {task.actionLabel}
                    </button>
                  )}
                </li>
              );
            })}
          </motion.ul>
        )}
      </AnimatePresence>
    </motion.div>
  );
}
