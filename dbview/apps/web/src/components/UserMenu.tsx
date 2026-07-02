import { useEffect, useRef, useState } from 'react';
import { LogOut, UserRound, Users } from 'lucide-react';
import { getCurrentUser, logoutRequest, subscribe } from '../lib/auth.js';
import { useAppStore } from '../store/app.js';
import type { UserPublic } from '@dbview/shared';

export function UserMenu() {
  const [user, setUser] = useState<UserPublic | null>(getCurrentUser());
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const setUsersOpen = useAppStore((s) => s.setUsersOpen);

  useEffect(() => subscribe(() => setUser(getCurrentUser())), []);

  useEffect(() => {
    if (!open) return;
    const handler = (e: MouseEvent) => {
      if (!ref.current?.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, [open]);

  if (!user) return null;

  const label = user.displayName ?? user.email;

  return (
    <div ref={ref} className="relative">
      <button
        data-tour="user-menu"
        onClick={() => setOpen((v) => !v)}
        className="btn-icon"
        aria-label={`Account: ${label}`}
        title={label}
      >
        <UserRound className="w-4 h-4" />
      </button>
      {open && (
        <div
          role="menu"
          className="absolute right-0 top-full mt-2 w-56 rounded-md border bg-surface-1 shadow-lg z-50 overflow-hidden"
          style={{ borderColor: 'rgb(var(--border-subtle))' }}
        >
          <div className="px-3 py-2 border-b" style={{ borderColor: 'rgb(var(--border-subtle))' }}>
            <div className="text-[12px] font-medium truncate">{label}</div>
            <div className="text-[10px] uppercase tracking-wide text-text-dim">{user.role}</div>
          </div>
          {user.role === 'admin' && (
            <button
              type="button"
              onClick={() => {
                setOpen(false);
                setUsersOpen(true);
              }}
              className="w-full flex items-center gap-2 px-3 py-2 text-[12px] hover:bg-surface-2 border-b"
              style={{ borderColor: 'rgb(var(--border-subtle))' }}
            >
              <Users className="w-3.5 h-3.5" />
              Manage users
            </button>
          )}
          <button
            type="button"
            onClick={() => void logoutRequest()}
            className="w-full flex items-center gap-2 px-3 py-2 text-[12px] hover:bg-surface-2"
          >
            <LogOut className="w-3.5 h-3.5" />
            Sign out
          </button>
        </div>
      )}
    </div>
  );
}
