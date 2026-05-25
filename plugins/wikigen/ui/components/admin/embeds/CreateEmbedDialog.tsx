/**
 * CreateEmbedDialog — form modale per creare un widget embed.
 *
 * Output success: ``EmbedWithToken`` con plaintext. Caller mostra
 * subito ``TokenRevealDialog`` perché il plaintext NON è recuperabile
 * dopo (token_hash storato server-side).
 */

import { useState } from 'react';
import { toast } from 'sonner';

import * as embedsApi from '../../../lib/api/embeds';
import type { EmbedWithToken } from '../../../lib/api/embeds';
import { Button, ModalShell } from '../../ui';

interface Props {
  open: boolean;
  onClose: () => void;
  onCreated: (result: EmbedWithToken) => void;
}

const SLUG_RE = /^[a-z0-9][a-z0-9._-]*$/;
const ORIGIN_RE = /^https?:\/\/[a-zA-Z0-9._-]+(?::\d{1,5})?$/;

export function CreateEmbedDialog({ open, onClose, onCreated }: Props) {
  const [slug, setSlug] = useState('');
  const [name, setName] = useState('');
  const [originsRaw, setOriginsRaw] = useState('');
  const [welcome, setWelcome] = useState('Ciao! Come posso aiutarti?');
  const [primary, setPrimary] = useState('#0ea5e9');
  const [position, setPosition] = useState<'bottom-right' | 'bottom-left'>('bottom-right');
  const [rateLimit, setRateLimit] = useState(30);
  const [submitting, setSubmitting] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const reset = () => {
    setSlug('');
    setName('');
    setOriginsRaw('');
    setWelcome('Ciao! Come posso aiutarti?');
    setPrimary('#0ea5e9');
    setPosition('bottom-right');
    setRateLimit(30);
    setErr(null);
  };

  const submit = async (ev: React.FormEvent) => {
    ev.preventDefault();
    setErr(null);
    if (!SLUG_RE.test(slug)) {
      setErr("Slug non valido: usa solo [a-z0-9._-], inizia con lettera/cifra.");
      return;
    }
    if (!name.trim()) {
      setErr('Nome obbligatorio.');
      return;
    }
    const origins = originsRaw
      .split('\n')
      .map((s) => s.trim().replace(/\/$/, ''))
      .filter((s) => s.length > 0);
    for (const o of origins) {
      if (!ORIGIN_RE.test(o)) {
        setErr(`Origin non valido: ${o}. Usa "https://host[:port]" senza path.`);
        return;
      }
    }
    setSubmitting(true);
    try {
      const result = await embedsApi.createEmbed({
        slug,
        name: name.trim(),
        origin_allowlist: origins,
        theme: { primary, position },
        welcome_message: welcome,
        rate_limit_per_minute: rateLimit,
      });
      toast.success(`Widget "${result.name}" creato`);
      reset();
      onCreated(result);
    } catch (e) {
      const msg = e instanceof Error ? e.message : 'errore creazione';
      setErr(msg);
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
      title="Nuovo widget embed"
      width="lg"
    >
      <form onSubmit={submit} className="space-y-4 p-1">
        <Row label="Slug">
          <input
            type="text"
            value={slug}
            onChange={(e) => setSlug(e.target.value)}
            placeholder="acme-website"
            className="input-sm w-full font-mono"
            required
            autoFocus
          />
        </Row>
        <Row label="Nome">
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Acme Website Chat"
            className="input-sm w-full"
            required
          />
        </Row>
        <Row label="Origini autorizzate" hint="Una per riga. Es: https://acme.com">
          <textarea
            value={originsRaw}
            onChange={(e) => setOriginsRaw(e.target.value)}
            rows={3}
            placeholder="https://acme.com&#10;https://www.acme.com"
            className="input-sm w-full font-mono"
          />
        </Row>
        <Row label="Messaggio di benvenuto">
          <input
            type="text"
            value={welcome}
            onChange={(e) => setWelcome(e.target.value)}
            maxLength={500}
            className="input-sm w-full"
          />
        </Row>
        <div className="grid grid-cols-3 gap-4">
          <Row label="Colore primario">
            <input
              type="color"
              value={primary}
              onChange={(e) => setPrimary(e.target.value)}
              className="h-8 w-full cursor-pointer rounded border border-[var(--color-border)]"
            />
          </Row>
          <Row label="Posizione">
            <select
              value={position}
              onChange={(e) =>
                setPosition(e.target.value === 'bottom-left' ? 'bottom-left' : 'bottom-right')
              }
              className="input-sm w-full"
            >
              <option value="bottom-right">In basso a destra</option>
              <option value="bottom-left">In basso a sinistra</option>
            </select>
          </Row>
          <Row label="Rate limit / min">
            <input
              type="number"
              min={0}
              max={600}
              value={rateLimit}
              onChange={(e) => setRateLimit(parseInt(e.target.value || '0', 10) || 0)}
              className="input-sm w-full"
            />
          </Row>
        </div>
        {err && (
          <div className="rounded border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-700">
            {err}
          </div>
        )}
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
            {submitting ? 'Creazione…' : 'Crea widget'}
          </Button>
        </div>
      </form>
    </ModalShell>
  );
}


function Row({
  label,
  hint,
  children,
}: {
  label: string;
  hint?: string;
  children: React.ReactNode;
}) {
  return (
    <label className="flex flex-col gap-1">
      <span className="text-[11px] font-medium text-ink uppercase tracking-wide">{label}</span>
      {children}
      {hint && <span className="text-[10px] text-ink-subtle">{hint}</span>}
    </label>
  );
}
