import {
  ReactNode,
  cloneElement,
  isValidElement,
  ReactElement,
  useEffect,
  useRef,
  useState,
} from 'react';

interface PopoverProps {
  trigger: ReactElement;
  children: ReactNode | ((close: () => void) => ReactNode);
  align?: 'left' | 'right';
  width?: number;
}

export function Popover({ trigger, children, align = 'right', width = 280 }: PopoverProps) {
  const [open, setOpen] = useState(false);
  const root = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const onDoc = (e: MouseEvent) => {
      if (!root.current) return;
      if (!root.current.contains(e.target as Node)) setOpen(false);
    };
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setOpen(false);
    };
    document.addEventListener('mousedown', onDoc);
    document.addEventListener('keydown', onKey);
    return () => {
      document.removeEventListener('mousedown', onDoc);
      document.removeEventListener('keydown', onKey);
    };
  }, [open]);

  const close = () => setOpen(false);

  const triggerEl = isValidElement(trigger)
    ? cloneElement(trigger as ReactElement<{ onClick?: (e: React.MouseEvent) => void }>, {
        onClick: (e: React.MouseEvent) => {
          e.stopPropagation();
          setOpen((s) => !s);
        },
      })
    : trigger;

  return (
    <div ref={root} className="relative">
      {triggerEl}
      {open && (
        <div
          className={`absolute top-full z-30 mt-1.5 ${
            align === 'right' ? 'right-0' : 'left-0'
          } overflow-hidden rounded-md border border-bg-line bg-bg-elevated shadow-xl ring-1 ring-bg-line/40 animate-enter-up`}
          style={{ width }}
        >
          {typeof children === 'function' ? children(close) : children}
        </div>
      )}
    </div>
  );
}

interface MenuItemProps {
  icon?: ReactNode;
  label: ReactNode;
  description?: ReactNode;
  onSelect?: () => void;
  href?: string;
  danger?: boolean;
  disabled?: boolean;
}

export function MenuItem({
  icon,
  label,
  description,
  onSelect,
  href,
  danger,
  disabled,
}: MenuItemProps) {
  const cls = `flex w-full items-start gap-2.5 px-3 py-2 text-left text-sm transition-colors ${
    disabled
      ? 'cursor-not-allowed text-text-subtle'
      : danger
        ? 'text-sev-critical hover:bg-sev-critical/10'
        : 'text-text-primary hover:bg-bg-hover/60'
  }`;
  const inner = (
    <>
      {icon && <span className="mt-0.5 shrink-0 text-text-muted">{icon}</span>}
      <span className="min-w-0 flex-1">
        <span className="block truncate">{label}</span>
        {description && (
          <span className="mt-0.5 block truncate text-xs text-text-muted">{description}</span>
        )}
      </span>
    </>
  );
  if (href && !disabled) {
    return (
      <a href={href} className={cls}>
        {inner}
      </a>
    );
  }
  return (
    <button type="button" className={cls} onClick={onSelect} disabled={disabled}>
      {inner}
    </button>
  );
}

export function MenuDivider() {
  return <div className="my-1 border-t border-bg-line/60" />;
}

export function MenuHeader({ children }: { children: ReactNode }) {
  return (
    <div className="px-3 pb-1 pt-2 text-2xs font-mono uppercase tracking-wider text-text-muted">
      {children}
    </div>
  );
}
