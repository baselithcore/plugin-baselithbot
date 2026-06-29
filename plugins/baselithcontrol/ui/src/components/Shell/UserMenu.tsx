import { useEffect, useLayoutEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { useTranslation } from 'react-i18next';
import { Shield, User, LogOut, ChevronDown, Gauge, UserCog } from 'lucide-react';
import { fetchMyLlmUsage, logout } from '@/lib/api';
import { useControlStore } from '@/store/useControlStore';
import { UsageGauge } from '@/components/widgets/UsageGauge';
import type { Me, MyLlmUsage } from '@/types';

/**
 * Top-right identity control. Clicking the name opens a compact dropdown showing
 * only the month-to-date LLM consumption (a quick glance), with links to the
 * full Account page and logout. The panel renders in a body portal so it never
 * inherits the topbar's backdrop-filter stacking/clip context.
 */
export function UserMenu({ me }: { me: Me }) {
  const { t } = useTranslation();
  const setTab = useControlStore((s) => s.setTab);
  const select = useControlStore((s) => s.select);
  const [open, setOpen] = useState(false);
  const [usage, setUsage] = useState<MyLlmUsage | null>(null);
  const [loading, setLoading] = useState(false);
  const [pos, setPos] = useState({ top: 0, right: 0 });
  const triggerRef = useRef<HTMLButtonElement>(null);
  const menuRef = useRef<HTMLDivElement>(null);

  // Anchor the portal under the trigger; keep it pinned on scroll/resize.
  useLayoutEffect(() => {
    if (!open) return;
    const place = () => {
      const r = triggerRef.current?.getBoundingClientRect();
      if (r) setPos({ top: r.bottom + 8, right: window.innerWidth - r.right });
    };
    place();
    window.addEventListener('resize', place);
    window.addEventListener('scroll', place, true);
    return () => {
      window.removeEventListener('resize', place);
      window.removeEventListener('scroll', place, true);
    };
  }, [open]);

  // Refetch each time the menu opens — cheap, and always shows current spend.
  useEffect(() => {
    if (!open) return;
    let alive = true;
    setLoading(true);
    fetchMyLlmUsage()
      .then((u) => alive && setUsage(u))
      .finally(() => alive && setLoading(false));
    return () => {
      alive = false;
    };
  }, [open]);

  // Dismiss on outside click / Escape — panel is portalled, so check both nodes.
  useEffect(() => {
    if (!open) return;
    const onDown = (e: MouseEvent) => {
      const target = e.target as Node;
      if (triggerRef.current?.contains(target) || menuRef.current?.contains(target)) return;
      setOpen(false);
    };
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && setOpen(false);
    document.addEventListener('mousedown', onDown);
    document.addEventListener('keydown', onKey);
    return () => {
      document.removeEventListener('mousedown', onDown);
      document.removeEventListener('keydown', onKey);
    };
  }, [open]);

  const name = me.display_name || me.username || me.email || me.user_id;
  const openAccount = () => {
    setOpen(false);
    select(null);
    setTab('account');
  };

  return (
    <div className="shrink-0">
      <button
        ref={triggerRef}
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-haspopup="menu"
        aria-expanded={open}
        title={name}
        className={`flex items-center gap-2 rounded-lg border px-2 py-1.5 transition ${
          open
            ? 'border-[var(--accent-border)] bg-[var(--accent-soft)]'
            : 'brd bg-[var(--surface-inset)] hover:bg-[var(--surface-2)]'
        }`}
      >
        <span
          className={`flex h-6 w-6 items-center justify-center rounded-md ${
            me.is_admin ? 'bg-[var(--accent-soft)] t-accent' : 'surf t-dim'
          }`}
        >
          {me.is_admin ? <Shield className="h-3.5 w-3.5" /> : <User className="h-3.5 w-3.5" />}
        </span>
        <span className="hidden text-left leading-tight lg:block">
          <span className="block text-[12px] font-semibold t-primary">{name}</span>
          <span className="block text-[10px] font-medium t-faint">
            {me.is_admin ? t('access.admin') : t('access.read_only')}
          </span>
        </span>
        <ChevronDown
          className={`h-3.5 w-3.5 t-faint transition-transform ${open ? 'rotate-180' : ''}`}
        />
      </button>

      {open &&
        createPortal(
          <div
            ref={menuRef}
            role="menu"
            style={{ position: 'fixed', top: pos.top, right: pos.right }}
            className="glass z-50 w-72 origin-top-right overflow-hidden p-0 shadow-xl"
          >
            {/* Cost glance — only the monthly LLM consumption lives here */}
            <div className="p-3">
              <div className="mb-2 flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-wide t-faint">
                <Gauge className="h-3.5 w-3.5" />
                {t('usage.title')}
              </div>
              <UsageGauge usage={usage} loading={loading} size="sm" moneyless />
            </div>

            {/* Full account page */}
            <button
              type="button"
              onClick={openAccount}
              className="flex w-full items-center gap-2 border-t brd px-3 py-2.5 text-[12px] font-medium t-dim transition hover:bg-[var(--surface-2)] hover:text-[var(--text)]"
            >
              <UserCog className="h-4 w-4" />
              {t('account.open')}
            </button>

            {/* Logout */}
            <button
              type="button"
              onClick={() => logout()}
              className="flex w-full items-center gap-2 border-t brd px-3 py-2.5 text-[12px] font-medium t-dim transition hover:bg-[var(--surface-2)] hover:text-rose-500"
            >
              <LogOut className="h-4 w-4" />
              {t('access.logout')}
            </button>
          </div>,
          document.body
        )}
    </div>
  );
}
