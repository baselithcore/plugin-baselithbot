import { useEffect } from 'react';
import { createPortal } from 'react-dom';
import { AnimatePresence, motion } from 'framer-motion';
import { FileJson, Maximize2, Minimize2, X } from 'lucide-react';
import { toast } from 'sonner';
import { extractProperties, formatValue } from './data.js';
import type { ResNode } from './types.js';
import { useResizableDrawer } from '../../lib/use-resizable-drawer.js';
import { ResizeHandle } from '../../components/detail-drawer/DrawerShell.js';

interface Props {
  node: ResNode | null;
  onClose: () => void;
}

export function NodeDetailDrawer({ node, onClose }: Props) {
  const open = !!node;
  const { width, isResizing, isExpanded, toggleExpanded, handleProps } = useResizableDrawer({
    storageKey: 'dbview.node-drawer.width',
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
  const raw = node?.raw;
  const labels = raw?._labels ?? [];
  const entries = raw ? extractProperties(raw) : [];
  return createPortal(
    <>
      {open && (
        <div
          onClick={onClose}
          className="fixed inset-0 z-40 bg-black/30 backdrop-blur-[2px] animate-fade-in"
          aria-hidden
        />
      )}
      <AnimatePresence>
        {open && raw && (
          <motion.aside
            key="node-detail-drawer-2d"
            role="dialog"
            aria-modal="false"
            aria-label="Node detail"
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
                <div className="text-[13px] font-semibold truncate flex items-center gap-2">
                  <span
                    className="w-2.5 h-2.5 rounded-full shrink-0"
                    style={{ background: node!.color }}
                    aria-hidden
                  />
                  <span>{node!.label}</span>
                </div>
                <div className="text-[10px] font-mono text-text-dim truncate">
                  {labels.length > 0 ? labels.map((l) => `:${l}`).join(' ') : 'node'} ·{' '}
                  {entries.length} props
                </div>
              </div>
              <div className="flex items-center gap-1 shrink-0">
                <button
                  onClick={() => {
                    navigator.clipboard.writeText(JSON.stringify(raw, null, 2));
                    toast.success('Node JSON copied');
                  }}
                  className="btn-icon"
                  title="Copy as JSON"
                >
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
            <div className="flex-1 min-h-0 overflow-auto p-3 flex flex-col gap-1">
              {entries.length === 0 && (
                <div className="text-[12px] text-text-dim italic px-3 py-2">No properties.</div>
              )}
              {entries.map(([key, value]) => (
                <div
                  key={key}
                  className="flex items-start justify-between gap-3 px-3 py-2 rounded-md text-[12px] font-mono"
                  style={{ background: 'rgb(var(--surface-2) / 0.4)' }}
                >
                  <span className="text-text-muted shrink-0">{key}</span>
                  <span className="text-text text-right break-all whitespace-pre-wrap">
                    {formatValue(value)}
                  </span>
                </div>
              ))}
            </div>
          </motion.aside>
        )}
      </AnimatePresence>
    </>,
    document.body
  );
}
