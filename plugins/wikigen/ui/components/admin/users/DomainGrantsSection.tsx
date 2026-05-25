import { AnimatePresence, motion } from 'framer-motion';
import { Globe, Plus, ShieldOff } from 'lucide-react';
import { useEffect, useMemo, useState } from 'react';
import type { TenantInfo } from '../../../lib/api/admin';
import type { RoleSummary, UserWithRoles } from '../../../lib/api/rbac';
import { Button, Callout, SectionHeader } from '../../ui';
import { Chip } from './atoms';
import { DomainPicker } from './DomainPicker';
import { GrantRow } from './GrantRow';

type AddPayload = { slug: string; roleId: string };

interface Props {
  user: UserWithRoles;
  tenants: TenantInfo[];
  roles: RoleSummary[];
  canManageRole: (r: RoleSummary) => boolean;
  busy: string | null;
  onAddGrant: (payload: AddPayload) => Promise<void> | void;
  onUpdateGrant: (payload: AddPayload) => Promise<void> | void;
  onRemoveGrant: (slug: string) => Promise<void> | void;
}

export function DomainGrantsSection({
  user,
  tenants,
  roles,
  canManageRole,
  busy,
  onAddGrant,
  onUpdateGrant,
  onRemoveGrant,
}: Props) {
  const [picker, setPicker] = useState<{ slug: string; roleId: string } | null>(null);
  const [editing, setEditing] = useState<string | null>(null);
  const [query, setQuery] = useState('');

  const tMap = useMemo(() => {
    const m = new Map<string, TenantInfo>();
    for (const t of tenants) m.set(t.name, t);
    return m;
  }, [tenants]);
  const assignableRoles = useMemo(() => roles.filter(canManageRole), [roles, canManageRole]);

  const isSuperuser = user.roles.some((r) => r.slug === 'superuser');
  const isAdmin = user.roles.some((r) => r.slug === 'admin');

  const grantedSet = useMemo(
    () => new Set(user.domain_grants.map((g) => g.domain_slug)),
    [user.domain_grants],
  );

  const available = useMemo(() => {
    const q = query.trim().toLowerCase();
    return tenants
      .filter((t) => !grantedSet.has(t.name))
      .filter((t) => {
        if (!q) return true;
        return (
          t.name.toLowerCase().includes(q) ||
          t.label.toLowerCase().includes(q) ||
          t.description.toLowerCase().includes(q)
        );
      })
      .sort((a, b) => Number(b.is_active) - Number(a.is_active) || a.label.localeCompare(b.label));
  }, [tenants, grantedSet, query]);

  const closePicker = () => {
    setPicker(null);
    setQuery('');
  };

  useEffect(() => {
    closePicker();
    setEditing(null);
  }, [user.id]);

  return (
    <section>
      <SectionHeader
        title="Accessi per dominio"
        icon={Globe}
        trailing={
          <div className="flex items-center gap-2">
            <Chip>{user.domain_grants.length}</Chip>
            <Button
              size="sm"
              variant="primary"
              leadingIcon={Plus}
              disabled={picker !== null || tenants.length === 0}
              onClick={() => setPicker({ slug: '', roleId: '' })}
            >
              Aggiungi
            </Button>
          </div>
        }
      />

      {isSuperuser && (
        <Callout tone="warning" icon={ShieldOff} className="mb-3">
          <strong>Superuser</strong> — i domain grants vengono <em>ignorati</em>: l’utente accede
          a tutti i domini con permessi pieni.
        </Callout>
      )}
      {!isSuperuser && isAdmin && (
        <Callout tone="info" className="mb-3">
          Ruolo <strong>admin</strong> attivo — accesso globale già concesso. I grant qui sotto
          servono per <em>override di ruolo</em> per singoli domini.
        </Callout>
      )}
      {!isSuperuser && !isAdmin && user.domain_grants.length === 0 && picker === null && (
        <EmptyState
          onAdd={() => setPicker({ slug: '', roleId: '' })}
          hasTenants={tenants.length > 0}
        />
      )}

      {user.domain_grants.length > 0 && (
        <ul className="mb-3 flex flex-col gap-1.5">
          {user.domain_grants.map((g) => (
            <GrantRow
              key={g.domain_slug}
              grant={g}
              tenant={tMap.get(g.domain_slug)}
              roles={assignableRoles}
              busy={busy}
              userId={user.id}
              isEditing={editing === g.domain_slug}
              onStartEdit={() => setEditing(g.domain_slug)}
              onCancelEdit={() => setEditing(null)}
              onSaveRole={async (roleId) => {
                await onUpdateGrant({ slug: g.domain_slug, roleId });
                setEditing(null);
              }}
              onRemove={() => onRemoveGrant(g.domain_slug)}
            />
          ))}
        </ul>
      )}

      <AnimatePresence initial={false}>
        {picker !== null && (
          <motion.div
            key="picker"
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.16, ease: 'easeOut' }}
            className="overflow-hidden"
          >
            <DomainPicker
              query={query}
              setQuery={setQuery}
              available={available}
              selected={picker.slug}
              roleId={picker.roleId}
              roles={assignableRoles}
              busy={busy === `add:${user.id}:${picker.slug}`}
              onSelect={(slug) =>
                setPicker((p) => (p ? { ...p, slug } : { slug, roleId: '' }))
              }
              onRoleChange={(roleId) => setPicker((p) => (p ? { ...p, roleId } : null))}
              onCancel={closePicker}
              onConfirm={async () => {
                if (!picker.slug) return;
                await onAddGrant({ slug: picker.slug, roleId: picker.roleId });
                closePicker();
              }}
            />
          </motion.div>
        )}
      </AnimatePresence>
    </section>
  );
}

function EmptyState({ onAdd, hasTenants }: { onAdd: () => void; hasTenants: boolean }) {
  return (
    <div className="mb-3 rounded-xl border border-dashed border-[var(--color-border)] bg-[var(--color-canvas-raised)] px-4 py-5 text-center">
      <Globe size={20} className="mx-auto mb-2 text-ink-subtle" aria-hidden />
      <p className="text-[12px] font-medium text-ink">Nessun accesso specifico</p>
      <p className="mx-auto mt-1 max-w-[28ch] text-[11px] leading-relaxed text-ink-subtle">
        L’utente accede a tutti i domini con i permessi del ruolo globale. Aggiungi un grant per
        limitare o sovrascrivere il ruolo su un dominio.
      </p>
      <Button
        className="mt-3"
        size="sm"
        variant="secondary"
        leadingIcon={Plus}
        onClick={onAdd}
        disabled={!hasTenants}
      >
        {hasTenants ? 'Aggiungi accesso' : 'Nessun dominio disponibile'}
      </Button>
    </div>
  );
}
