import { Copy, Mail, ShieldCheck } from 'lucide-react';
import { useState } from 'react';
import { toast } from 'sonner';
import * as authApi from '../../../lib/api/auth';
import type { RoleSummary } from '../../../lib/api/rbac';
import { Button, Callout, ModalShell } from '../../ui';

export function InviteDialog({
  open,
  roles,
  onClose,
  onCreated,
}: {
  open: boolean;
  roles: RoleSummary[];
  onClose: () => void;
  onCreated: () => void;
}) {
  const [email, setEmail] = useState('');
  const [name, setName] = useState('');
  const [roleSlug, setRoleSlug] = useState('user');
  const [ttl, setTtl] = useState(72);
  const [submitting, setSubmitting] = useState(false);
  const [acceptUrl, setAcceptUrl] = useState<string | null>(null);

  const reset = () => {
    setEmail('');
    setName('');
    setRoleSlug('user');
    setTtl(72);
    setAcceptUrl(null);
  };

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      const r = await authApi.createInvite({
        email: email.trim(),
        display_name: name.trim() || undefined,
        role_slug: roleSlug || null,
        ttl_hours: ttl,
      });
      setAcceptUrl(window.location.origin + r.accept_url);
      onCreated();
      toast.success('Invito creato');
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'invito fallito');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <ModalShell
      open={open}
      onClose={() => {
        reset();
        onClose();
      }}
      title="Invita utente"
      icon={Mail}
      width="md"
    >
      {acceptUrl ? (
        <div className="flex flex-col gap-3 p-5 text-xs">
          <Callout tone="success">
            Invito creato. Condividi il link sotto — single-use, scade fra {ttl}h.
          </Callout>
          <div className="flex items-center gap-2 rounded border border-[var(--color-border)] bg-[var(--color-surface)] px-2 py-1.5">
            <code className="flex-1 truncate text-[11px]">{acceptUrl}</code>
            <button
              type="button"
              className="btn-icon"
              onClick={() => {
                navigator.clipboard.writeText(acceptUrl);
                toast.success('Copiato');
              }}
              aria-label="copia link"
            >
              <Copy size={12} />
            </button>
          </div>
          <div className="flex justify-end gap-2 pt-2">
            <Button variant="secondary" size="sm" onClick={reset}>
              Nuovo invito
            </Button>
            <Button
              variant="primary"
              size="sm"
              onClick={() => {
                reset();
                onClose();
              }}
            >
              Chiudi
            </Button>
          </div>
        </div>
      ) : (
        <form onSubmit={submit} className="flex flex-col gap-3 p-5 text-xs">
          <label className="flex flex-col gap-1">
            <span className="text-[10px] uppercase text-ink-subtle">Email</span>
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="input-sm"
              autoComplete="email"
              autoFocus
            />
          </label>
          <label className="flex flex-col gap-1">
            <span className="text-[10px] uppercase text-ink-subtle">Nome (opz.)</span>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="input-sm"
            />
          </label>
          <div className="grid grid-cols-2 gap-3">
            <label className="flex flex-col gap-1">
              <span className="text-[10px] uppercase text-ink-subtle">Ruolo iniziale</span>
              <select
                value={roleSlug}
                onChange={(e) => setRoleSlug(e.target.value)}
                className="input-sm"
              >
                {roles.map((r) => (
                  <option key={r.id} value={r.slug}>
                    {r.slug}
                  </option>
                ))}
              </select>
            </label>
            <label className="flex flex-col gap-1">
              <span className="text-[10px] uppercase text-ink-subtle">Validità (ore)</span>
              <input
                type="number"
                min={1}
                max={720}
                value={ttl}
                onChange={(e) => setTtl(parseInt(e.target.value) || 72)}
                className="input-sm"
              />
            </label>
          </div>
          <div className="flex justify-end gap-2 pt-2">
            <Button
              type="button"
              variant="secondary"
              size="sm"
              onClick={() => {
                reset();
                onClose();
              }}
            >
              Annulla
            </Button>
            <Button type="submit" variant="primary" size="sm" disabled={submitting}>
              <ShieldCheck size={12} />
              {submitting ? 'Creazione…' : 'Crea invito'}
            </Button>
          </div>
        </form>
      )}
    </ModalShell>
  );
}
