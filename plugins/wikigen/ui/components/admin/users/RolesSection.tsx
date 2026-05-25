import { Check, Lock, ShieldCheck } from 'lucide-react';
import type { RoleSummary, UserWithRoles } from '../../../lib/api/rbac';
import { cn } from '../../../lib/cn';
import { SectionHeader } from '../../ui';

const ROLE_DESCRIPTIONS: Record<string, string> = {
  superuser: 'Pieno controllo della piattaforma. Bypassa i domain grants.',
  admin: 'Amministra il tenant: utenti, ruoli, ingest, branding.',
  moderator: 'Cura contenuti del vault e modera feedback.',
  user: 'Accesso standard a chat e wiki dei domini consentiti.',
};

const ROLE_ACCENT: Record<string, string> = {
  superuser: 'data-[on=true]:border-rose-500/50 data-[on=true]:bg-rose-500/10',
  admin: 'data-[on=true]:border-amber-500/50 data-[on=true]:bg-amber-500/10',
  moderator: 'data-[on=true]:border-[var(--color-brand-ring)] data-[on=true]:bg-[var(--color-brand-soft)]',
  user: 'data-[on=true]:border-emerald-500/40 data-[on=true]:bg-emerald-500/10',
};

export function RolesSection({
  user,
  roles,
  canManageRole,
  busy,
  onToggleRole,
}: {
  user: UserWithRoles;
  roles: RoleSummary[];
  canManageRole: (r: RoleSummary) => boolean;
  busy: string | null;
  onToggleRole: (u: UserWithRoles, r: RoleSummary) => void;
}) {
  return (
    <section className="mb-6">
      <SectionHeader
        title="Ruoli di sistema"
        icon={ShieldCheck}
        trailing={
          <span className="text-[10px] text-ink-subtle">{user.roles.length} attivi</span>
        }
      />
      <p className="mb-2 text-[11px] leading-relaxed text-ink-subtle">
        Definiscono i permessi globali. I domain grants estendono o restringono l’accesso per
        specifici domini.
      </p>
      <ul className="grid grid-cols-1 gap-1.5">
        {roles.map((r) => {
          const has = user.roles.some((ur) => ur.id === r.id);
          const allowed = canManageRole(r);
          const k = `role:${user.id}:${r.id}`;
          const pending = busy === k;
          return (
            <li key={r.id}>
              <button
                type="button"
                disabled={!allowed || pending}
                data-on={has}
                onClick={() => onToggleRole(user, r)}
                className={cn(
                  'focus-ring group w-full rounded-lg border border-[var(--color-border)]',
                  'bg-[var(--color-canvas-raised)] px-3 py-2 text-left transition-colors',
                  'hover:border-[var(--color-border-strong)] hover:bg-[var(--color-surface)]',
                  'disabled:cursor-not-allowed disabled:opacity-50',
                  ROLE_ACCENT[r.slug] ?? '',
                )}
                aria-pressed={has}
                title={!allowed ? 'Permesso insufficiente per gestire questo ruolo' : undefined}
              >
                <div className="flex items-center justify-between gap-3">
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-1.5">
                      <span className="truncate text-[12px] font-semibold text-ink">
                        {r.name}
                      </span>
                      <code className="rounded bg-[var(--color-surface)] px-1 text-[10px] text-ink-subtle">
                        {r.slug}
                      </code>
                    </div>
                    <p className="mt-0.5 line-clamp-2 text-[11px] text-ink-subtle">
                      {ROLE_DESCRIPTIONS[r.slug] ?? r.description}
                    </p>
                  </div>
                  <div className="shrink-0">
                    {!allowed ? (
                      <Lock size={13} className="text-ink-subtle" aria-hidden />
                    ) : has ? (
                      <span
                        className={cn(
                          'inline-flex size-5 items-center justify-center rounded-full',
                          'bg-emerald-500 text-white shadow-sm',
                        )}
                      >
                        <Check size={11} strokeWidth={3} aria-hidden />
                      </span>
                    ) : (
                      <span className="inline-block size-5 rounded-full border border-dashed border-[var(--color-border-strong)] opacity-70 group-hover:opacity-100" />
                    )}
                  </div>
                </div>
              </button>
            </li>
          );
        })}
      </ul>
    </section>
  );
}
