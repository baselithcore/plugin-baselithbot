import { cn } from '@/lib/cn';
import { Kbd } from '@/components/Kbd';
import type { SlashCommand } from './menus';

interface Props {
  commands: SlashCommand[];
  index: number;
  coords: { left: number; top: number };
  onPick: (cmd: SlashCommand) => void;
}

/** Floating '/' block-insert menu, anchored at the caret, grouped by section. */
export function SlashMenu({ commands, index, coords, onPick }: Props) {
  if (!commands.length) return null;

  // Preserve the flat order (and thus the keyboard-nav index) while drawing a
  // header whenever the group changes.
  let prevGroup = '';
  return (
    <div
      className="bb-pop fixed z-50 max-h-80 w-60 overflow-y-auto rounded-lg border border-[var(--color-border)] bg-[var(--color-elevated)] p-1 shadow-xl"
      style={{ left: coords.left, top: coords.top + 6 }}
    >
      {commands.map((cmd, i) => {
        const header = cmd.group !== prevGroup ? cmd.group : null;
        prevGroup = cmd.group;
        return (
          <div key={cmd.id}>
            {header && (
              <div className="px-2.5 pb-0.5 pt-1.5 text-[10px] font-semibold uppercase tracking-wide text-[var(--color-faint)]">
                {header}
              </div>
            )}
            <button
              onMouseDown={(e) => {
                e.preventDefault();
                onPick(cmd);
              }}
              className={cn(
                'flex w-full items-center justify-between rounded-md px-2.5 py-1.5 text-left text-sm',
                i === index
                  ? 'bg-[var(--color-accent-soft)] text-[var(--color-text)]'
                  : 'text-[var(--color-muted)] hover:bg-[var(--color-surface)]'
              )}
            >
              <span>{cmd.label}</span>
              <Kbd keys={cmd.hint} />
            </button>
          </div>
        );
      })}
    </div>
  );
}
