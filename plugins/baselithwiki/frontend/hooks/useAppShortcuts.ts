import { useEffect } from 'react';

interface ShortcutHandlers {
  onNewChat: () => void;
  onToggleSidebar: () => void;
  onTogglePalette: () => void;
  onToggleSettings: () => void;
  onToggleUpload: () => void;
  onToggleWizard: () => void;
  onToggleHelp: () => void;
}

/**
 * Global keyboard shortcuts for the app shell. Mounted once at the top level.
 * `?` ignored when the user is typing in a field; modifier shortcuts always fire.
 */
export function useAppShortcuts(h: ShortcutHandlers) {
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      const mod = e.metaKey || e.ctrlKey;
      const target = e.target as HTMLElement | null;
      const inField =
        !!target &&
        (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA' || target.isContentEditable);
      if (mod && e.key === 'k') {
        e.preventDefault();
        h.onNewChat();
      } else if (mod && e.key === 'b') {
        e.preventDefault();
        h.onToggleSidebar();
      } else if (mod && e.key === '/') {
        e.preventDefault();
        h.onTogglePalette();
      } else if (mod && e.key === ',') {
        e.preventDefault();
        h.onToggleSettings();
      } else if (mod && e.key === 'u') {
        e.preventDefault();
        h.onToggleUpload();
      } else if (mod && e.shiftKey && (e.key === 'N' || e.key === 'n')) {
        e.preventDefault();
        h.onToggleWizard();
      } else if (e.key === '?' && !inField) {
        e.preventDefault();
        h.onToggleHelp();
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
    // handlers usually re-create each render; effect cleans up before re-binding.
  }, [h]);
}
