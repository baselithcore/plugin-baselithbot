/**
 * CreateUserDialog — admin-driven user creation.
 *
 * L'admin sceglie email + password iniziale + ruolo. Il backend setta
 * ``password_must_change=true``: al primo login il server risponde
 * 403 con header ``X-Password-Must-Change`` su qualsiasi rotta
 * protetta, e ``App.tsx`` redirige l'utente a ``/auth/password`` per
 * scegliersi la sua. Workflow alternativo agli inviti via email,
 * utile per onboarding offline / batch da CSV.
 *
 * Generatore password opzionale (32 hex char = 128 bit entropy);
 * l'admin la copia e la consegna al destinatario via canale sicuro.
 */

import { Copy, Eye, EyeOff, KeyRound, RefreshCw, UserPlus } from 'lucide-react';
import { useEffect, useMemo, useState } from 'react';
import { toast } from 'sonner';

import * as rbacApi from '../../../lib/api/rbac';
import type { RoleSummary } from '../../../lib/api/rbac';
import { Button, Callout, ModalShell } from '../../ui';

interface Props {
  open: boolean;
  roles: RoleSummary[];
  /** ruoli che l'actor può assegnare (rbac.assign.<slug> richiesto) */
  assignableRoles: RoleSummary[];
  onClose: () => void;
  onCreated: () => void;
}

function generatePassword(): string {
  const bytes = new Uint8Array(16);
  crypto.getRandomValues(bytes);
  // 32 hex char base; aggiungiamo un simbolo + maiuscola per soddisfare
  // policy server (min 12, mai vincolate alla classe ma utile come segnale).
  const hex = Array.from(bytes, (b) => b.toString(16).padStart(2, '0')).join('');
  return `A!${hex}`;
}

export function CreateUserDialog({ open, roles, assignableRoles, onClose, onCreated }: Props) {
  const [email, setEmail] = useState('');
  const [displayName, setDisplayName] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [roleSlug, setRoleSlug] = useState('user');
  const [submitting, setSubmitting] = useState(false);
  const [createdInfo, setCreatedInfo] = useState<{ email: string; password: string } | null>(null);

  // Default role: prima entry assegnabile (di norma "user"); fallback
  // al primo system role disponibile.
  const defaultRole = useMemo(() => {
    if (assignableRoles.some((r) => r.slug === 'user')) return 'user';
    return assignableRoles[0]?.slug ?? roles[0]?.slug ?? 'user';
  }, [assignableRoles, roles]);

  const reset = () => {
    setEmail('');
    setDisplayName('');
    setPassword('');
    setShowPassword(false);
    setRoleSlug(defaultRole);
    setCreatedInfo(null);
  };

  useEffect(() => {
    if (open) {
      reset();
      setRoleSlug(defaultRole);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, defaultRole]);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (password.length < 12) {
      toast.error('Password troppo corta (min 12 caratteri)');
      return;
    }
    setSubmitting(true);
    try {
      await rbacApi.createUser({
        email: email.trim(),
        password,
        display_name: displayName.trim() || undefined,
        role_slug: roleSlug || 'user',
      });
      setCreatedInfo({ email: email.trim(), password });
      onCreated();
      toast.success('Utente creato — cambio password forzato al primo accesso');
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'creazione utente fallita');
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
      title="Crea utente"
      icon={UserPlus}
      width="md"
    >
      {createdInfo ? (
        <div className="flex flex-col gap-3 p-5 text-xs">
          <Callout tone="success">
            Utente creato. Condividi credenziali via canale sicuro — al primo accesso verrà
            obbligato a cambiarla.
          </Callout>
          <div className="flex flex-col gap-1">
            <span className="text-[10px] uppercase text-ink-subtle">Email</span>
            <div className="flex items-center gap-2 rounded border border-[var(--color-border)] bg-[var(--color-surface)] px-2 py-1.5">
              <code className="flex-1 truncate text-[11px]">{createdInfo.email}</code>
              <button
                type="button"
                className="btn-icon"
                onClick={() => {
                  navigator.clipboard.writeText(createdInfo.email);
                  toast.success('Email copiata');
                }}
                aria-label="copia email"
              >
                <Copy size={12} />
              </button>
            </div>
          </div>
          <div className="flex flex-col gap-1">
            <span className="text-[10px] uppercase text-ink-subtle">Password iniziale</span>
            <div className="flex items-center gap-2 rounded border border-[var(--color-border)] bg-[var(--color-surface)] px-2 py-1.5">
              <code className="flex-1 truncate text-[11px] font-mono">{createdInfo.password}</code>
              <button
                type="button"
                className="btn-icon"
                onClick={() => {
                  navigator.clipboard.writeText(createdInfo.password);
                  toast.success('Password copiata');
                }}
                aria-label="copia password"
              >
                <Copy size={12} />
              </button>
            </div>
          </div>
          <div className="flex justify-end gap-2 pt-2">
            <Button variant="secondary" size="sm" onClick={reset}>
              Crea altro utente
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
              maxLength={120}
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
              className="input-sm"
            />
          </label>
          <label className="flex flex-col gap-1">
            <span className="text-[10px] uppercase text-ink-subtle">
              Password iniziale (min 12 char)
            </span>
            <div className="flex items-center gap-1">
              <input
                type={showPassword ? 'text' : 'password'}
                required
                minLength={12}
                maxLength={128}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="input-sm flex-1 font-mono"
                autoComplete="new-password"
              />
              <button
                type="button"
                className="btn-icon"
                onClick={() => setShowPassword((v) => !v)}
                aria-label={showPassword ? 'nascondi password' : 'mostra password'}
                title={showPassword ? 'nascondi' : 'mostra'}
              >
                {showPassword ? <EyeOff size={12} /> : <Eye size={12} />}
              </button>
              <button
                type="button"
                className="btn-icon"
                onClick={() => {
                  setPassword(generatePassword());
                  setShowPassword(true);
                }}
                aria-label="genera password casuale"
                title="genera"
              >
                <RefreshCw size={12} />
              </button>
            </div>
            <span className="text-[10px] text-ink-subtle">
              L'utente sarà obbligato a cambiarla al primo accesso.
            </span>
          </label>
          <label className="flex flex-col gap-1">
            <span className="text-[10px] uppercase text-ink-subtle">Ruolo iniziale</span>
            <select
              value={roleSlug}
              onChange={(e) => setRoleSlug(e.target.value)}
              className="input-sm"
            >
              {assignableRoles.map((r) => (
                <option key={r.id} value={r.slug}>
                  {r.slug}
                </option>
              ))}
            </select>
          </label>
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
              <KeyRound size={12} />
              {submitting ? 'Creazione…' : 'Crea utente'}
            </Button>
          </div>
        </form>
      )}
    </ModalShell>
  );
}
