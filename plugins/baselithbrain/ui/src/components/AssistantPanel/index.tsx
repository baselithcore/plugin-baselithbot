import { useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { AnimatePresence, motion } from 'motion/react';
import {
  MessageSquareText,
  X,
  MessageSquarePlus,
  Link2,
  ScrollText,
  Tags,
  Wand2,
} from 'lucide-react';
import { useBrain } from '@/store';
import { api } from '@/lib/api';
import { drawerVariants } from '@/lib/motion';
import { Bubble } from './Bubble';
import { Welcome } from './Welcome';
import { Composer } from './Composer';
import { ConversationMenu } from './ConversationMenu';
import { useChat } from './useChat';

const NOTE_ACTIONS = [
  { id: 'summarize', label: 'Summarize', icon: ScrollText },
  { id: 'improve', label: 'Improve', icon: Wand2 },
  { id: 'autotag', label: 'Auto-tag', icon: Tags },
  { id: 'suggest_links', label: 'Suggest links', icon: Link2 },
] as const;

/** Chat-with-your-notes assistant: persisted threads, RAG answers, note actions. */
export function AssistantPanel() {
  const { t } = useTranslation();
  const open = useBrain((s) => s.assistantOpen);
  const setOpen = useBrain((s) => s.setAssistant);
  const active = useBrain((s) => s.active);
  const openNote = useBrain((s) => s.openNote);
  const openWiki = useBrain((s) => s.openWiki);

  const { msgs, busy, loadingThread, send, research, stop, newChat, runAction } = useChat();
  const [input, setInput] = useState('');
  const [configured, setConfigured] = useState<boolean | null>(null);
  const scroller = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (open && configured === null) {
      api
        .aiStatus()
        .then((s) => setConfigured(s.configured))
        .catch(() => setConfigured(false));
    }
  }, [open, configured]);

  useEffect(() => {
    scroller.current?.scrollTo({ top: scroller.current.scrollHeight, behavior: 'smooth' });
  }, [msgs, busy]);

  const onSend = () => {
    const q = input.trim();
    if (!q) return;
    setInput('');
    void send(q);
  };

  const onResearch = () => {
    const q = input.trim();
    if (!q) return;
    setInput('');
    void research(q);
  };

  return (
    <>
      <AnimatePresence>
        {!open && (
          <motion.button
            key="fab"
            title={t('assistant.fab')}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 8 }}
            whileTap={{ scale: 0.97 }}
            transition={{ duration: 0.16, ease: [0.22, 1, 0.36, 1] }}
            onClick={() => setOpen(true)}
            className="bb-gradient bb-btn-glow fixed bottom-6 right-6 z-30 flex items-center gap-2 rounded-full px-4 py-2.5 text-sm font-medium text-white"
          >
            <MessageSquareText className="size-4" />
            {t('assistant.fab')}
          </motion.button>
        )}
      </AnimatePresence>

      <AnimatePresence>
        {open && (
          <>
            <motion.div
              key="scrim"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.2 }}
              onClick={() => setOpen(false)}
              className="fixed inset-0 z-30 bg-[var(--color-overlay)] backdrop-blur-[2px] lg:hidden"
            />
            <motion.aside
              key="drawer"
              variants={drawerVariants}
              initial="hidden"
              animate="show"
              exit="exit"
              className="bb-solid fixed right-3 top-3 bottom-3 z-30 flex w-[27rem] max-w-[94vw] flex-col overflow-hidden rounded-[var(--radius-lg)] shadow-2xl"
            >
              <header className="flex items-center gap-1.5 border-b border-[var(--color-border)] px-3 py-3">
                <span className="bb-gradient flex size-6 items-center justify-center rounded-lg text-white">
                  <MessageSquareText className="size-3.5" />
                </span>
                <ConversationMenu onPick={() => setInput('')} />
                <div className="ml-auto flex items-center gap-1">
                  <button
                    title={t('assistant.newChat')}
                    onClick={() => {
                      newChat();
                      setInput('');
                    }}
                    className="rounded-lg p-1.5 text-[var(--color-muted)] hover:bg-[var(--color-elevated)]"
                  >
                    <MessageSquarePlus className="size-4" />
                  </button>
                  <button
                    title={t('assistant.close')}
                    onClick={() => setOpen(false)}
                    className="rounded-lg p-1.5 text-[var(--color-muted)] hover:bg-[var(--color-elevated)]"
                  >
                    <X className="size-4" />
                  </button>
                </div>
              </header>

              {configured === false && (
                <div className="border-b border-[var(--color-border)] bg-[var(--color-accent-soft)] px-4 py-2 text-xs text-[var(--color-link)]">
                  {t('assistant.noLlm')}
                </div>
              )}

              {active && (
                <div className="flex flex-wrap gap-1.5 border-b border-[var(--color-border)] px-3 py-2">
                  {NOTE_ACTIONS.map((a) => (
                    <motion.button
                      key={a.id}
                      disabled={busy}
                      whileTap={{ scale: 0.94 }}
                      onClick={() => void runAction(a.id)}
                      className="flex items-center gap-1 rounded-lg border border-[var(--color-border)] px-2 py-1 text-xs text-[var(--color-muted)] transition hover:border-[var(--color-accent)] hover:bg-[var(--color-accent-soft)] hover:text-[var(--color-text)] disabled:opacity-40"
                    >
                      <a.icon className="size-3" />
                      {t(
                        a.id === 'suggest_links'
                          ? 'actions.suggestLinks'
                          : a.id === 'autotag'
                            ? 'actions.autotag'
                            : `actions.${a.id}`
                      )}
                    </motion.button>
                  ))}
                </div>
              )}

              <div ref={scroller} className="flex-1 space-y-4 overflow-y-auto p-4">
                {loadingThread ? (
                  <p className="py-6 text-center text-xs text-[var(--color-faint)]">
                    {t('assistant.loading')}
                  </p>
                ) : !msgs.length ? (
                  <Welcome onAsk={(q) => setInput(q)} />
                ) : (
                  msgs.map((m, i) => (
                    <Bubble
                      key={i}
                      msg={m}
                      streaming={busy && i === msgs.length - 1 && m.role === 'assistant'}
                      onOpen={openNote}
                      onWiki={openWiki}
                    />
                  ))
                )}
              </div>

              <Composer
                value={input}
                busy={busy}
                onChange={setInput}
                onSend={onSend}
                onResearch={onResearch}
                onStop={stop}
              />
            </motion.aside>
          </>
        )}
      </AnimatePresence>
    </>
  );
}
