/**
 * EmbedDetailPanel — drawer di edit per un singolo widget embed.
 *
 * Field PATCH-able:
 * - name / description (cosmetici)
 * - origin_allowlist (sicurezza)
 * - theme.primary / theme.position (branding)
 * - welcome_message / suggested_questions
 * - rate_limit_per_minute
 * - is_enabled (kill switch — disabilita senza eliminare)
 *
 * NON modificabili da update: ``slug`` (parte dell'identity record) e
 * ``token`` (usa rotate endpoint).
 */

import { Save } from 'lucide-react';
import { useEffect, useState } from 'react';
import { toast } from 'sonner';

import * as embedsApi from '../../../lib/api/embeds';
import type { EmbedSummary } from '../../../lib/api/embeds';
import { Button, Switch } from '../../ui';

interface Props {
  embed: EmbedSummary;
  onChanged: () => void;
}

export function EmbedDetailPanel({ embed, onChanged }: Props) {
  const [name, setName] = useState(embed.name);
  const [description, setDescription] = useState(embed.description);
  const [originsRaw, setOriginsRaw] = useState(embed.origin_allowlist.join('\n'));
  const [welcome, setWelcome] = useState(embed.welcome_message);
  const [suggestionsRaw, setSuggestionsRaw] = useState(embed.suggested_questions.join('\n'));
  const [primary, setPrimary] = useState(embed.theme.primary ?? '#0ea5e9');
  const [position, setPosition] = useState<'bottom-right' | 'bottom-left'>(
    embed.theme.position ?? 'bottom-right'
  );
  const [rateLimit, setRateLimit] = useState(embed.rate_limit_per_minute);
  const [enabled, setEnabled] = useState(embed.is_enabled);
  const [saving, setSaving] = useState(false);

  // Reset locale quando cambia il record selezionato.
  useEffect(() => {
    setName(embed.name);
    setDescription(embed.description);
    setOriginsRaw(embed.origin_allowlist.join('\n'));
    setWelcome(embed.welcome_message);
    setSuggestionsRaw(embed.suggested_questions.join('\n'));
    setPrimary(embed.theme.primary ?? '#0ea5e9');
    setPosition(embed.theme.position ?? 'bottom-right');
    setRateLimit(embed.rate_limit_per_minute);
    setEnabled(embed.is_enabled);
  }, [embed]);

  const save = async () => {
    const origins = originsRaw
      .split('\n')
      .map((s) => s.trim().replace(/\/$/, ''))
      .filter(Boolean);
    const suggestions = suggestionsRaw
      .split('\n')
      .map((s) => s.trim())
      .filter(Boolean)
      .slice(0, 8);
    setSaving(true);
    try {
      await embedsApi.updateEmbed(embed.id, {
        name: name.trim(),
        description,
        origin_allowlist: origins,
        theme: { ...embed.theme, primary, position },
        welcome_message: welcome,
        suggested_questions: suggestions,
        rate_limit_per_minute: rateLimit,
        is_enabled: enabled,
      });
      toast.success('Salvato');
      onChanged();
    } catch (e) {
      toast.error(e instanceof Error ? e.message : 'salvataggio fallito');
    } finally {
      setSaving(false);
    }
  };

  return (
    <aside className="flex w-[420px] flex-col border-l border-[var(--color-border)] bg-[var(--color-surface)]">
      <header className="flex items-center gap-3 border-b border-[var(--color-border)] px-5 py-3">
        <div className="flex flex-1 flex-col leading-tight">
          <span className="text-[10px] uppercase text-ink-subtle font-medium">Widget</span>
          <span className="text-sm font-semibold">{embed.slug}</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-[11px] text-ink-subtle">{enabled ? 'Attivo' : 'Disattivo'}</span>
          <Switch checked={enabled} onChange={setEnabled} label="Attivo/Disattivo" hideLabel />
        </div>
      </header>

      <div className="flex-1 overflow-y-auto space-y-4 px-5 py-4">
        <Row label="Nome">
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="input-sm w-full"
          />
        </Row>
        <Row label="Descrizione">
          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            rows={2}
            className="input-sm w-full"
          />
        </Row>
        <Row
          label="Origini autorizzate"
          hint="Una per riga. Senza origini il widget è inutilizzabile."
        >
          <textarea
            value={originsRaw}
            onChange={(e) => setOriginsRaw(e.target.value)}
            rows={4}
            placeholder="https://acme.com"
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
        <Row label="Domande suggerite" hint="Una per riga. Max 8.">
          <textarea
            value={suggestionsRaw}
            onChange={(e) => setSuggestionsRaw(e.target.value)}
            rows={4}
            className="input-sm w-full"
          />
        </Row>
        <div className="grid grid-cols-2 gap-3">
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
              <option value="bottom-right">Bottom-right</option>
              <option value="bottom-left">Bottom-left</option>
            </select>
          </Row>
        </div>
        <Row label="Rate limit / minuto (per IP)">
          <input
            type="number"
            min={0}
            max={600}
            value={rateLimit}
            onChange={(e) => setRateLimit(parseInt(e.target.value || '0', 10) || 0)}
            className="input-sm w-full"
          />
        </Row>

        <div className="rounded-md border border-[var(--color-border)] bg-zinc-50 p-3 text-[11px] text-ink-subtle">
          <div>
            Token prefix: <span className="font-mono">{embed.token_prefix}…</span>
          </div>
          {embed.last_used_at && <div>Ultimo uso: {embed.last_used_at}</div>}
          <div>Creato: {embed.created_at ?? '—'}</div>
        </div>
      </div>

      <footer className="flex justify-end gap-2 border-t border-[var(--color-border)] px-5 py-3">
        <Button variant="primary" size="sm" onClick={() => void save()} disabled={saving}>
          <Save size={13} />
          {saving ? 'Salvataggio…' : 'Salva'}
        </Button>
      </footer>
    </aside>
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
