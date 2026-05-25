import { AnimatePresence, motion } from 'framer-motion';
import { X } from 'lucide-react';
import { useEffect, useId } from 'react';
import { cn } from '../../lib/cn';
import { useFocusTrap } from '../../hooks/useFocusTrap';
import { IconButton } from './IconButton';

type Width = 'sm' | 'md' | 'lg' | 'xl' | '2xl';

const MAX_W: Record<Width, string> = {
  sm: 'max-w-md',
  md: 'max-w-lg',
  lg: 'max-w-xl',
  xl: 'max-w-2xl',
  '2xl': 'max-w-3xl',
};

interface ModalShellProps {
  open: boolean;
  onClose: () => void;
  /** Header title — text or rich JSX. Used as accessible name. */
  title: React.ReactNode;
  /** Plain string fallback when title is JSX (for aria-label). */
  ariaLabel?: string;
  icon?: React.ComponentType<{ size?: number; className?: string }>;
  /** Optional secondary text after title in the header. Hidden on mobile. */
  subtitle?: React.ReactNode;
  /** Right-side controls inside the header, before the close X. */
  headerActions?: React.ReactNode;
  /** Disables Esc and X (e.g. blocking first-run wizard). */
  blocking?: boolean;
  width?: Width;
  /** Custom panel className for layout overrides (flex, height, etc). */
  panelClassName?: string;
  /** Render footer pinned at the bottom of the panel. */
  footer?: React.ReactNode;
  children: React.ReactNode;
  /** Extra description id list. The body always falls back to a generated one. */
  describedBy?: string;
}

/**
 * Accessible modal shell:
 * - role="dialog" + aria-modal
 * - Esc closes (unless blocking)
 * - focus trap while open
 * - title is wired as the dialog accessible name (aria-labelledby)
 * - body content is described by aria-describedby
 *
 * Replaces the ad-hoc modal-overlay/modal-panel/modal-header pattern repeated
 * across UploadModal/SettingsModal/HelpModal.
 */
export function ModalShell({
  open,
  onClose,
  title,
  ariaLabel,
  icon: Icon,
  subtitle,
  headerActions,
  blocking = false,
  width = 'md',
  panelClassName,
  footer,
  children,
  describedBy,
}: ModalShellProps) {
  const titleId = useId();
  const bodyId = useId();
  const dialogRef = useFocusTrap<HTMLDivElement>(open);

  useEffect(() => {
    if (!open || blocking) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [open, onClose, blocking]);

  return (
    <AnimatePresence>
      {open && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.12 }}
          onClick={() => !blocking && onClose()}
          className="modal-overlay"
          role="dialog"
          aria-modal="true"
          aria-labelledby={titleId}
          aria-describedby={describedBy ? `${describedBy} ${bodyId}` : bodyId}
          aria-label={ariaLabel}
        >
          <motion.div
            ref={dialogRef}
            initial={{ opacity: 0, scale: 0.96, y: 6 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.96, y: 6 }}
            transition={{ duration: 0.14 }}
            onClick={(e) => e.stopPropagation()}
            className={cn(
              'modal-panel flex max-h-[calc(100vh-1.5rem)] flex-col',
              MAX_W[width],
              panelClassName,
            )}
          >
            <header className="modal-header">
              <div className="inline-flex min-w-0 items-center gap-2">
                {Icon && <Icon size={14} className="shrink-0 text-[var(--color-brand)]" />}
                <span id={titleId} className="truncate text-sm font-semibold text-ink">
                  {title}
                </span>
                {subtitle && (
                  <span className="ml-1 hidden text-[10px] text-ink-subtle sm:inline">
                    {subtitle}
                  </span>
                )}
              </div>
              <div className="flex items-center gap-1">
                {headerActions}
                {!blocking && (
                  <IconButton icon={X} aria-label="chiudi" size="sm" onClick={onClose} />
                )}
              </div>
            </header>
            <div id={bodyId} className="flex min-h-0 flex-1 flex-col">
              {children}
            </div>
            {footer && (
              <footer className="border-t border-[var(--color-border)] px-5 py-3">{footer}</footer>
            )}
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
