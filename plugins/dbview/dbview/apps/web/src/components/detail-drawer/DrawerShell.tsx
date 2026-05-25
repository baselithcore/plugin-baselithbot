import { useEffect } from 'react';
import { createPortal } from 'react-dom';
import { AnimatePresence, motion } from 'framer-motion';
import * as Tabs from '@radix-ui/react-tabs';
import { FileJson, GripVertical, Maximize2, Minimize2, X } from 'lucide-react';
import { useResizableDrawer } from '../../lib/use-resizable-drawer.js';

interface DrawerShellProps {
  open: boolean;
  onClose: () => void;
  title: React.ReactNode;
  subtitle: string;
  onCopy: () => void;
  children: React.ReactNode;
}

/**
 * Hand-rolled drawer. Previously used Radix `Dialog` wrapped in `AnimatePresence`
 * with `forceMount`, but that combination left the body in a `pointer-events:
 * none` / focus-trapped state after the close transition, freezing the page.
 *
 * We avoid all of that here: a plain portal + framer-motion AnimatePresence on
 * the visual elements, with manual Esc + backdrop-click handlers. No focus
 * trap and no body lock means closing always returns the page to a fully
 * interactive state.
 */
export function DrawerShell({
  open,
  onClose,
  title,
  subtitle,
  onCopy,
  children,
}: DrawerShellProps) {
  const { width, isResizing, isExpanded, toggleExpanded, handleProps } = useResizableDrawer({
    storageKey: 'dbview.drawer.width',
  });

  useEffect(() => {
    if (!open) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [open, onClose]);

  if (typeof document === 'undefined') return null;

  return createPortal(
    <>
      {/* Backdrop unmounts instantly on close (no exit animation) so it never
          lingers as a fixed inset-0 block-everything element while the panel
          finishes its slide-out. */}
      {open && (
        <div
          onClick={onClose}
          className="fixed inset-0 z-40"
          style={{ background: 'transparent' }}
          aria-hidden
        />
      )}
      <AnimatePresence>
        {open && (
          <motion.aside
            key="drawer-panel"
            role="dialog"
            aria-modal="false"
            aria-label={typeof subtitle === 'string' ? subtitle : 'Detail panel'}
            initial={{ x: '100%' }}
            animate={{ x: 0 }}
            exit={{ x: '100%' }}
            transition={isResizing ? { duration: 0 } : { duration: 0.28, ease: [0.22, 1, 0.36, 1] }}
            className="fixed top-0 right-0 z-50 h-full max-w-[95vw] flex flex-col border-l shadow-2xl pointer-events-auto"
            style={{
              width: `${width}px`,
              background:
                'linear-gradient(180deg, rgb(var(--surface-elevated)), rgb(var(--surface-1)))',
              borderColor: 'rgb(var(--border-subtle))',
              contain: 'layout',
            }}
          >
            <ResizeHandle isResizing={isResizing} {...handleProps} />
            <div
              className="flex items-center justify-between gap-3 px-4 h-12 border-b shrink-0"
              style={{ borderColor: 'rgb(var(--border-subtle))' }}
            >
              <div className="flex flex-col min-w-0">
                <div className="text-[13px] font-semibold truncate">{title}</div>
                <div className="text-[10px] font-mono text-text-dim truncate">{subtitle}</div>
              </div>
              <div className="flex items-center gap-1 shrink-0">
                <button onClick={onCopy} className="btn-icon" title="Copy as JSON">
                  <FileJson className="w-3.5 h-3.5" />
                </button>
                <button
                  onClick={toggleExpanded}
                  className="btn-icon"
                  title={isExpanded ? 'Restore width' : 'Expand panel'}
                  aria-label={isExpanded ? 'Restore width' : 'Expand panel'}
                  aria-pressed={isExpanded}
                >
                  {isExpanded ? (
                    <Minimize2 className="w-3.5 h-3.5" />
                  ) : (
                    <Maximize2 className="w-3.5 h-3.5" />
                  )}
                </button>
                <button onClick={onClose} className="btn-icon" aria-label="Close">
                  <X className="w-4 h-4" />
                </button>
              </div>
            </div>
            <div className="flex-1 min-h-0 overflow-hidden flex flex-col">{children}</div>
          </motion.aside>
        )}
      </AnimatePresence>
    </>,
    document.body,
  );
}

interface ResizeHandleProps {
  isResizing: boolean;
  onPointerDown: (e: React.PointerEvent<HTMLDivElement>) => void;
  onDoubleClick: () => void;
  onKeyDown: (e: React.KeyboardEvent<HTMLDivElement>) => void;
}

export function ResizeHandle({
  isResizing,
  onPointerDown,
  onDoubleClick,
  onKeyDown,
}: ResizeHandleProps) {
  const active = isResizing;
  return (
    <div
      role="separator"
      aria-orientation="vertical"
      aria-label="Resize panel — drag, double-click to reset, arrow keys to nudge"
      tabIndex={0}
      onPointerDown={onPointerDown}
      onDoubleClick={onDoubleClick}
      onKeyDown={onKeyDown}
      title="Drag to resize · double-click to reset"
      className="group absolute left-0 top-0 h-full w-3 -translate-x-1/2 cursor-col-resize z-10 focus:outline-none"
      style={{ touchAction: 'none' }}
    >
      <div
        className="absolute inset-y-0 left-1/2 w-px group-hover:bg-[rgb(var(--accent))] group-focus-visible:bg-[rgb(var(--accent))]"
        style={{
          transform: 'translateX(-50%)',
          background: active ? 'rgb(var(--accent))' : 'rgb(var(--border-subtle))',
        }}
        aria-hidden
      />
      <div
        className="absolute top-1/2 left-1/2 flex items-center justify-center rounded-md border shadow-sm group-hover:scale-110 group-focus-visible:scale-110 group-active:scale-95"
        style={{
          width: 14,
          height: 28,
          transform: 'translate3d(-50%, -50%, 0)',
          transition:
            'transform 150ms ease, background-color 150ms ease, color 150ms ease, border-color 150ms ease',
          willChange: 'transform',
          background: active ? 'rgb(var(--accent))' : 'rgb(var(--surface-elevated))',
          borderColor: active ? 'rgb(var(--accent))' : 'rgb(var(--border-subtle))',
          color: active ? 'rgb(var(--accent-fg))' : 'rgb(var(--text-muted))',
        }}
        aria-hidden
      >
        <GripVertical className="w-3 h-3" strokeWidth={2} />
      </div>
    </div>
  );
}

export function DrawerTab({
  value,
  active,
  icon,
  children,
}: {
  value: string;
  active: boolean;
  icon: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <Tabs.Trigger
      value={value}
      className="relative flex items-center gap-1.5 px-3 h-9 text-[12px] font-medium text-text-muted data-[state=active]:text-accent transition-colors hover:text-text"
    >
      {icon}
      <span>{children}</span>
      {active && (
        <motion.span
          layoutId="drawer-tab-indicator"
          className="absolute left-2 right-2 -bottom-px h-0.5 rounded-full bg-accent"
          transition={{ duration: 0.28, ease: [0.22, 1, 0.36, 1] }}
        />
      )}
    </Tabs.Trigger>
  );
}
