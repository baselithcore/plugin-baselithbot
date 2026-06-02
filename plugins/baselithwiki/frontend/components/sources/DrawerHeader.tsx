import { BookOpen, X } from 'lucide-react';
import { IconButton } from '../ui';

export function DrawerHeader({ count, onClose }: { count: number; onClose: () => void }) {
  return (
    <header className="flex items-center justify-between border-b border-[var(--color-border)] bg-[var(--color-surface)]/40 px-4 py-3">
      <div className="flex min-w-0 items-center gap-2">
        <div className="grid size-7 shrink-0 place-items-center rounded-md bg-[var(--color-brand-soft)] text-[var(--color-brand)]">
          <BookOpen size={13} aria-hidden />
        </div>
        <div className="min-w-0">
          <div className="text-sm font-semibold leading-tight text-ink">Fonti</div>
          <div className="text-[10px] leading-tight text-ink-subtle">
            {count} {count === 1 ? 'documento' : 'documenti'} citati
          </div>
        </div>
      </div>
      <IconButton icon={X} aria-label="chiudi pannello fonti" size="sm" onClick={onClose} />
    </header>
  );
}
