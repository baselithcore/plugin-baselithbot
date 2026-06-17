import { motion } from 'motion/react';
import { Send, Square, Telescope } from 'lucide-react';
import { Kbd, MOD } from '../Kbd';

/** Chat input box with send / deep-research / stop affordances + key hints. */
export function Composer({
  value,
  busy,
  onChange,
  onSend,
  onResearch,
  onStop,
}: {
  value: string;
  busy: boolean;
  onChange: (v: string) => void;
  onSend: () => void;
  onResearch: () => void;
  onStop: () => void;
}) {
  return (
    <div className="border-t border-[var(--color-border)] p-3">
      <div className="flex items-end gap-2">
        <textarea
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault();
              onSend();
            }
          }}
          rows={1}
          placeholder="Ask your knowledge base…"
          className="max-h-32 flex-1 resize-none rounded-xl border border-[var(--color-border)] bg-[var(--color-bg)]/60 px-3.5 py-2.5 text-sm outline-none transition placeholder:text-[var(--color-faint)] focus:border-[var(--color-accent)] focus:shadow-[0_0_0_3px_var(--color-accent-soft)]"
        />
        {busy ? (
          <motion.button
            whileTap={{ scale: 0.92 }}
            onClick={onStop}
            title="Stop"
            className="rounded-xl border border-[var(--color-border)] p-2.5 text-[var(--color-muted)] hover:bg-[var(--color-elevated)]"
          >
            <Square className="size-4" />
          </motion.button>
        ) : (
          <>
            <motion.button
              whileTap={{ scale: 0.92 }}
              onClick={onResearch}
              disabled={!value.trim()}
              title="Deep research — multi-hop reasoning across your notes"
              className="rounded-xl border border-[var(--color-border)] p-2.5 text-[var(--color-muted)] transition hover:border-[var(--color-accent)] hover:bg-[var(--color-accent-soft)] hover:text-[var(--color-text)] disabled:opacity-40"
            >
              <Telescope className="size-4" />
            </motion.button>
            <motion.button
              whileTap={{ scale: 0.92 }}
              onClick={onSend}
              disabled={!value.trim()}
              title="Send"
              className="bb-gradient bb-btn-glow rounded-xl p-2.5 text-white disabled:opacity-40 disabled:shadow-none"
            >
              <Send className="size-4" />
            </motion.button>
          </>
        )}
      </div>
      <p className="mt-2 text-center text-[10px] text-[var(--color-faint)]">
        <Kbd keys="↵" /> send · <Telescope className="inline size-2.5" /> research ·{' '}
        <Kbd keys={`${MOD}J`} /> toggle
      </p>
    </div>
  );
}
