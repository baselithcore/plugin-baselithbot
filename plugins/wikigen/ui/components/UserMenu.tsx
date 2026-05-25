/**
 * UserMenu (Fase 6.1).
 *
 * Avatar trigger in header → popover con: email, role, link a memorie,
 * logout. Solo se utente loggato; in modalità anonima/legacy non
 * renderizza nulla (App.tsx skip).
 */

import {
  type KeyboardEvent as ReactKeyboardEvent,
  useEffect,
  useId,
  useRef,
  useState,
} from 'react';
import {
  Brain,
  Building2,
  Check,
  ChevronDown,
  Copy,
  LogOut,
  Mail,
  Shield,
  User,
} from 'lucide-react';

import { useAuth } from '../contexts/AuthContext';

interface UserMenuProps {
  onOpenMemories: () => void;
}

export function UserMenu({ onOpenMemories }: UserMenuProps) {
  const { user, logout, can } = useAuth();
  const [open, setOpen] = useState(false);
  const [copiedTenant, setCopiedTenant] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const itemRefs = useRef<Array<HTMLButtonElement | null>>([]);
  const menuId = useId();

  useEffect(() => {
    if (!open) return;
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    const esc = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        setOpen(false);
        triggerRef.current?.focus();
      }
    };
    window.addEventListener('mousedown', handler);
    window.addEventListener('keydown', esc);
    return () => {
      window.removeEventListener('mousedown', handler);
      window.removeEventListener('keydown', esc);
    };
  }, [open]);

  useEffect(() => {
    if (!open) return;
    const t = window.setTimeout(() => itemRefs.current[0]?.focus(), 0);
    return () => window.clearTimeout(t);
  }, [open]);

  useEffect(() => {
    if (!copiedTenant) return;
    const t = window.setTimeout(() => setCopiedTenant(false), 1600);
    return () => window.clearTimeout(t);
  }, [copiedTenant]);

  if (!user) return null;

  const initial = (user.display_name || user.email)[0]?.toUpperCase() || '?';
  const isAdmin = user.role === 'admin';
  const displayName = user.display_name || user.email;
  const roleLabel = isAdmin ? 'Amministratore' : 'Utente';
  const shortTenantId = user.tenant_id
    ? `${user.tenant_id.slice(0, 8)}…${user.tenant_id.slice(-4)}`
    : 'n/d';

  const getMenuItems = () =>
    itemRefs.current.filter((item): item is HTMLButtonElement => item !== null);

  const focusMenuItem = (delta: number) => {
    const items = getMenuItems();
    if (items.length === 0) return;
    const current = document.activeElement;
    const currentIndex = items.findIndex((item) => item === current);
    const nextIndex = currentIndex < 0 ? 0 : (currentIndex + delta + items.length) % items.length;
    items[nextIndex]?.focus();
  };

  const handleMenuKeyDown = (e: ReactKeyboardEvent<HTMLDivElement>) => {
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      focusMenuItem(1);
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      focusMenuItem(-1);
    } else if (e.key === 'Home') {
      e.preventDefault();
      getMenuItems()[0]?.focus();
    } else if (e.key === 'End') {
      e.preventDefault();
      const items = getMenuItems();
      items[items.length - 1]?.focus();
    }
  };

  const copyTenantId = async () => {
    try {
      await navigator.clipboard.writeText(user.tenant_id);
      setCopiedTenant(true);
    } catch {
      setCopiedTenant(false);
    }
  };

  return (
    <div ref={ref} className="relative">
      <button
        ref={triggerRef}
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-haspopup="menu"
        aria-expanded={open}
        aria-controls={open ? menuId : undefined}
        className="focus-ring flex min-h-9 max-w-[13rem] items-center gap-2 rounded-lg border border-[var(--color-border)] bg-[var(--color-canvas-raised)] px-1.5 py-1 text-xs text-ink-muted shadow-xs transition-colors hover:border-[var(--color-border-strong)] hover:bg-[var(--color-surface)] hover:text-ink"
      >
        <span className="flex h-6 w-6 items-center justify-center rounded-full bg-[var(--color-brand)] text-[11px] font-semibold text-white">
          {initial}
        </span>
        <span className="hidden min-w-0 max-w-[8rem] truncate text-left font-medium text-ink md:block">
          {displayName}
        </span>
        <ChevronDown
          size={12}
          className={
            open ? 'shrink-0 rotate-180 transition-transform' : 'shrink-0 transition-transform'
          }
          aria-hidden
        />
      </button>

      {open && (
        <div
          id={menuId}
          role="menu"
          aria-label="menu utente"
          onKeyDown={handleMenuKeyDown}
          className="absolute right-0 z-30 mt-2 w-72 max-w-[calc(100vw-1rem)] overflow-hidden rounded-lg border border-[var(--color-border)] bg-[var(--color-canvas-raised)] shadow-xl"
        >
          <div className="border-b border-[var(--color-border)] px-3 py-3">
            <div className="flex items-start gap-2.5">
              <span className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-[var(--color-brand)] text-xs font-semibold text-white">
                {initial}
              </span>
              <div className="min-w-0 flex-1">
                <div className="truncate text-sm font-semibold text-ink" title={displayName}>
                  {displayName}
                </div>
                <div className="mt-1 flex min-w-0 items-center gap-1.5 text-[11px] text-ink-muted">
                  <Mail size={12} className="shrink-0" aria-hidden />
                  <span className="truncate" title={user.email}>
                    {user.email}
                  </span>
                </div>
              </div>
            </div>

            <div className="mt-3 grid gap-1.5 text-[11px]">
              <div className="flex items-center justify-between gap-2 rounded-md bg-[var(--color-surface)] px-2 py-1.5">
                <span className="inline-flex min-w-0 items-center gap-1.5 text-ink-muted">
                  {isAdmin ? (
                    <Shield size={12} className="shrink-0 text-[var(--color-brand)]" aria-hidden />
                  ) : (
                    <User size={12} className="shrink-0" aria-hidden />
                  )}
                  Ruolo
                </span>
                <span className="truncate font-medium text-ink">{roleLabel}</span>
              </div>
              <div className="flex items-center justify-between gap-2 rounded-md bg-[var(--color-surface)] px-2 py-1.5">
                <span className="inline-flex min-w-0 items-center gap-1.5 text-ink-muted">
                  <Building2 size={12} className="shrink-0" aria-hidden />
                  Tenant
                </span>
                <button
                  ref={(el) => {
                    itemRefs.current[0] = el;
                  }}
                  type="button"
                  role="menuitem"
                  onClick={() => void copyTenantId()}
                  className="focus-ring inline-flex min-w-0 items-center gap-1 rounded px-1 py-0.5 font-mono text-[10px] text-ink hover:bg-[var(--color-canvas-raised)]"
                  aria-label="copia id tenant"
                  title={user.tenant_id}
                >
                  <span className="truncate">{shortTenantId}</span>
                  {copiedTenant ? <Check size={11} aria-hidden /> : <Copy size={11} aria-hidden />}
                </button>
              </div>
            </div>
          </div>

          {can('memory.read') && (
            <>
              <button
                ref={(el) => {
                  itemRefs.current[1] = el;
                }}
                type="button"
                role="menuitem"
                onClick={() => {
                  setOpen(false);
                  onOpenMemories();
                }}
                className="flex w-full items-center gap-2 px-3 py-2 text-left text-xs text-ink-muted transition-colors hover:bg-[var(--color-surface)] hover:text-ink"
              >
                <Brain size={14} aria-hidden />
                <span>Memorie personali</span>
              </button>

              <div className="border-t border-[var(--color-border)]" />
            </>
          )}

          <button
            ref={(el) => {
              itemRefs.current[2] = el;
            }}
            type="button"
            role="menuitem"
            onClick={() => {
              setOpen(false);
              void logout();
            }}
            className="flex w-full items-center gap-2 px-3 py-2 text-left text-xs text-[var(--color-danger)] transition-colors hover:bg-[var(--color-danger)]/10"
          >
            <LogOut size={14} aria-hidden />
            <span>Esci</span>
          </button>
        </div>
      )}
    </div>
  );
}
