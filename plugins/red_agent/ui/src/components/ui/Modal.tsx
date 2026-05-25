import { useEffect } from 'react';
import { createPortal } from 'react-dom';
import { Icon } from './Icon';

export function Modal({
  open,
  onClose,
  children,
  size = 'lg',
  ariaLabel,
}: {
  open: boolean;
  onClose: () => void;
  children: React.ReactNode;
  size?: 'md' | 'lg' | 'xl';
  ariaLabel?: string;
}) {
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    document.addEventListener('keydown', onKey);
    const prevOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => {
      document.removeEventListener('keydown', onKey);
      document.body.style.overflow = prevOverflow;
    };
  }, [open, onClose]);

  if (!open) return null;

  const widthCls = size === 'md' ? 'max-w-2xl' : size === 'xl' ? 'max-w-6xl' : 'max-w-4xl';

  return createPortal(
    <div
      className="fixed inset-0 z-50 flex items-start justify-center bg-bg-base/70 backdrop-blur-sm px-4 py-8 overflow-y-auto animate-enter-fade"
      role="dialog"
      aria-modal="true"
      aria-label={ariaLabel}
      onClick={onClose}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        className={`relative w-full ${widthCls} rounded-lg border border-bg-line bg-bg-elevated shadow-2xl ring-1 ring-black/40 animate-enter-up`}
      >
        <button
          type="button"
          onClick={onClose}
          aria-label="Close"
          className="absolute right-3 top-3 z-10 grid h-8 w-8 place-items-center rounded text-text-muted transition-colors hover:bg-bg-hover hover:text-text-primary"
        >
          <Icon.X size={14} />
        </button>
        {children}
      </div>
    </div>,
    document.body
  );
}
