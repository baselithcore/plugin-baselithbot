import { useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { AnimatePresence, motion } from 'motion/react';
import {
  MoreHorizontal,
  History,
  FileStack,
  Download,
  Archive,
  Pin,
  PinOff,
  Maximize2,
} from 'lucide-react';
import { useBrain } from '@/store';
import { api } from '@/lib/api';

interface Item {
  id: string;
  label: string;
  icon: React.ReactNode;
  run: () => void;
}

/** Overflow menu for note-level + vault-level actions (keeps the Topbar lean). */
export function MoreMenu() {
  const { t } = useTranslation();
  const active = useBrain((s) => s.active);
  const pinned = useBrain((s) => s.pinned);
  const togglePin = useBrain((s) => s.togglePin);
  const setModal = useBrain((s) => s.setModal);
  const toggleFocus = useBrain((s) => s.toggleFocus);
  const activeWorkspace = useBrain((s) => s.activeWorkspace);
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const onClick = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    window.addEventListener('mousedown', onClick);
    return () => window.removeEventListener('mousedown', onClick);
  }, [open]);

  const isPinned = active ? pinned.includes(active.id) : false;
  const items: Item[] = [];
  if (active) {
    items.push(
      {
        id: 'pin',
        label: isPinned ? t('more.unpin') : t('more.pin'),
        icon: isPinned ? <PinOff className="size-4" /> : <Pin className="size-4" />,
        run: () => togglePin(active.id),
      },
      {
        id: 'history',
        label: t('more.history'),
        icon: <History className="size-4" />,
        run: () => setModal('history'),
      },
      {
        id: 'export-note',
        label: t('more.exportNote'),
        icon: <Download className="size-4" />,
        run: () => void api.downloadNote(active.id),
      }
    );
  }
  items.push(
    {
      id: 'templates',
      label: t('more.templates'),
      icon: <FileStack className="size-4" />,
      run: () => setModal('templates'),
    },
    {
      id: 'export-vault',
      label: t('more.exportVault'),
      icon: <Archive className="size-4" />,
      run: () => void api.downloadVault(activeWorkspace),
    },
    {
      id: 'focus',
      label: t('more.focus'),
      icon: <Maximize2 className="size-4" />,
      run: toggleFocus,
    }
  );

  return (
    <div ref={ref} className="relative">
      <button
        title={t('more.label')}
        onClick={() => setOpen((v) => !v)}
        className="flex items-center rounded-xl px-2 py-1.5 text-[var(--color-muted)] transition-colors hover:bg-[var(--color-elevated)] hover:text-[var(--color-text)]"
      >
        <MoreHorizontal className="size-4" />
      </button>
      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0, y: -4 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -4 }}
            transition={{ duration: 0.12 }}
            className="bb-solid absolute right-0 top-full z-50 mt-1 w-56 overflow-hidden rounded-lg p-1"
          >
            {items.map((item) => (
              <button
                key={item.id}
                onClick={() => {
                  item.run();
                  setOpen(false);
                }}
                className="flex w-full items-center gap-2.5 rounded-md px-2.5 py-2 text-left text-sm text-[var(--color-muted)] transition-colors hover:bg-[var(--color-elevated)] hover:text-[var(--color-text)]"
              >
                <span className="text-[var(--color-faint)]">{item.icon}</span>
                {item.label}
              </button>
            ))}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
