/**
 * CreateGroupDialog — modal "Nuovo gruppo".
 *
 * Pattern coerente con InviteDialog: ModalShell + input-sm + Button
 * primary/secondary. Slug auto-derivato dal nome finché l'utente non
 * lo edita esplicitamente; pattern server-side `^[a-z0-9][a-z0-9._-]*$`.
 */

import { UsersRound } from 'lucide-react';
import { useEffect, useState } from 'react';
import { toast } from 'sonner';

import * as groupsApi from '../../../lib/api/groups';
import { Button, Callout, ModalShell } from '../../ui';

interface Props {
  open: boolean;
  onClose: () => void;
  onCreated: () => void;
}

function slugify(input: string): string {
  return input
    .toLowerCase()
    .trim()
    .replace(/[^a-z0-9._-]+/g, '-')
    .replace(/^-+|-+$/g, '')
    .slice(0, 64);
}

export function CreateGroupDialog({ open, onClose, onCreated }: Props) {
  const [name, setName] = useState('');
  const [slug, setSlug] = useState('');
  const [slugTouched, setSlugTouched] = useState(false);
  const [description, setDescription] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const reset = () => {
    setName('');
    setSlug('');
    setSlugTouched(false);
    setDescription('');
    setError(null);
  };

  useEffect(() => {
    if (open) reset();
  }, [open]);

  useEffect(() => {
    if (!slugTouched) setSlug(slugify(name));
  }, [name, slugTouched]);

  const submit = async (ev: React.FormEvent) => {
    ev.preventDefault();
    if (!name.trim() || !slug.trim()) {
      setError('Nome e slug obbligatori.');
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      await groupsApi.createGroup({ slug, name, description });
      onCreated();
      toast.success(`Gruppo "${name}" creato`);
      reset();
      onClose();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'creazione fallita');
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
      title="Nuovo gruppo"
      icon={UsersRound}
      width="md"
    >
      <form onSubmit={submit} className="flex flex-col gap-3 p-5 text-xs">
        <label className="flex flex-col gap-1">
          <span className="text-[10px] uppercase text-ink-subtle">Nome</span>
          <input
            type="text"
            required
            maxLength={120}
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="input-sm"
            autoFocus
          />
        </label>
        <label className="flex flex-col gap-1">
          <span className="text-[10px] uppercase text-ink-subtle">Slug</span>
          <input
            type="text"
            required
            minLength={2}
            maxLength={64}
            pattern="^[a-z0-9][a-z0-9._-]*$"
            value={slug}
            onChange={(e) => {
              setSlug(e.target.value);
              setSlugTouched(true);
            }}
            className="input-sm font-mono"
          />
          <span className="text-[10px] text-ink-subtle">
            Identificatore univoco nel tenant. Lowercase, no spazi.
          </span>
        </label>
        <label className="flex flex-col gap-1">
          <span className="text-[10px] uppercase text-ink-subtle">Descrizione</span>
          <textarea
            rows={2}
            maxLength={500}
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            className="input-sm resize-none"
          />
        </label>
        {error && <Callout tone="warning">{error}</Callout>}
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
            <UsersRound size={12} />
            {submitting ? 'Creazione…' : 'Crea gruppo'}
          </Button>
        </div>
      </form>
    </ModalShell>
  );
}
