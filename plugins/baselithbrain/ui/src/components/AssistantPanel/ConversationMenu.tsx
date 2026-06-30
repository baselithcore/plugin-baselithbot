import { useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Check, ChevronDown, MessageSquarePlus, Pencil, Trash2, X } from 'lucide-react';
import { useBrain } from '@/store';

/** Thread switcher: pick a past conversation, rename/delete it, or start fresh.
 *
 * Threads are persisted server-side and workspace-scoped, so this is the entry
 * point to the assistant's long-term conversational memory.
 */
export function ConversationMenu({ onPick }: { onPick: () => void }) {
  const { t } = useTranslation();
  const conversations = useBrain((s) => s.conversations);
  const activeId = useBrain((s) => s.activeConversationId);
  const setActive = useBrain((s) => s.setActiveConversation);
  const remove = useBrain((s) => s.deleteConversation);
  const rename = useBrain((s) => s.renameConversation);

  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState<string | null>(null);
  const [draft, setDraft] = useState('');
  const wrap = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const onDoc = (e: MouseEvent) => {
      if (wrap.current && !wrap.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener('mousedown', onDoc);
    return () => document.removeEventListener('mousedown', onDoc);
  }, [open]);

  const current = conversations.find((c) => c.id === activeId);
  const label = current?.title ?? t('assistant.newChat');

  const pick = (id: string | null) => {
    setActive(id);
    setEditing(null);
    setOpen(false);
    onPick();
  };

  const commitRename = (id: string) => {
    const title = draft.trim();
    if (title) void rename(id, title);
    setEditing(null);
  };

  return (
    <div ref={wrap} className="relative min-w-0">
      <button
        onClick={() => setOpen((v) => !v)}
        title={t('assistant.conversations')}
        className="flex max-w-[12rem] items-center gap-1 rounded-lg px-2 py-1 text-xs font-medium text-[var(--color-muted)] hover:bg-[var(--color-elevated)]"
      >
        <span className="truncate">{label}</span>
        <ChevronDown className="size-3 shrink-0" />
      </button>

      {open && (
        <div className="bb-pop bb-solid absolute left-0 top-full z-40 mt-1.5 w-72 overflow-hidden rounded-xl shadow-2xl">
          <button
            onClick={() => pick(null)}
            className="flex w-full items-center gap-2 border-b border-[var(--color-border)] px-3 py-2 text-left text-xs font-medium text-[var(--color-accent)] hover:bg-[var(--color-surface)]"
          >
            <MessageSquarePlus className="size-3.5" />
            {t('assistant.newChat')}
          </button>

          <div className="max-h-72 overflow-y-auto py-1">
            {conversations.length === 0 ? (
              <p className="px-3 py-3 text-center text-[11px] text-[var(--color-faint)]">
                {t('assistant.noConversations')}
              </p>
            ) : (
              conversations.map((c) => (
                <div
                  key={c.id}
                  className={`group flex items-center gap-1 px-2 py-1.5 text-xs ${
                    c.id === activeId ? 'bg-[var(--color-surface)]' : ''
                  }`}
                >
                  {editing === c.id ? (
                    <input
                      autoFocus
                      value={draft}
                      onChange={(e) => setDraft(e.target.value)}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter') commitRename(c.id);
                        if (e.key === 'Escape') setEditing(null);
                      }}
                      onBlur={() => commitRename(c.id)}
                      className="flex-1 rounded border border-[var(--color-accent)] bg-[var(--color-bg)] px-1.5 py-1 outline-none"
                    />
                  ) : (
                    <button
                      onClick={() => pick(c.id)}
                      className="flex-1 truncate py-1 text-left text-[var(--color-text)] hover:text-[var(--color-accent)]"
                      title={c.title}
                    >
                      {c.id === activeId && (
                        <Check className="mr-1 inline size-3 text-[var(--color-accent)]" />
                      )}
                      {c.title}
                      <span className="ml-1 text-[var(--color-faint)]">· {c.message_count}</span>
                    </button>
                  )}

                  {editing === c.id ? (
                    <button
                      onClick={() => setEditing(null)}
                      className="rounded p-1 text-[var(--color-faint)] hover:text-[var(--color-text)]"
                      title={t('common.cancel')}
                    >
                      <X className="size-3" />
                    </button>
                  ) : (
                    <div className="flex shrink-0 opacity-0 transition group-hover:opacity-100">
                      <button
                        onClick={() => {
                          setEditing(c.id);
                          setDraft(c.title);
                        }}
                        className="rounded p-1 text-[var(--color-faint)] hover:text-[var(--color-text)]"
                        title={t('assistant.rename')}
                      >
                        <Pencil className="size-3" />
                      </button>
                      <button
                        onClick={() => void remove(c.id)}
                        className="rounded p-1 text-[var(--color-faint)] hover:text-red-500"
                        title={t('common.delete')}
                      >
                        <Trash2 className="size-3" />
                      </button>
                    </div>
                  )}
                </div>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  );
}
