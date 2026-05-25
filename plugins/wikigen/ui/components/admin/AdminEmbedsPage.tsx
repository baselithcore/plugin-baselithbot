/**
 * AdminEmbedsPage — gestione widget chat embeddabili (mig 017).
 *
 * Pattern table + drawer detail allineato a ``AdminGroupsPage``:
 *
 * - lista a sinistra con ``slug``, origins count, rate-limit, enabled flag.
 * - drawer dettaglio a destra per editing inline (allowlist, theme,
 *   welcome message, rate limit, on/off).
 * - dialog modale per create + token-reveal (plaintext mostrato SOLO
 *   alla creazione/rotate, mai più recuperabile).
 *
 * Gating UI: tutto richiede ``admin.embed.manage``. Se il caller non lo
 * ha, la pagina mostra solo un Callout.
 */

import { Copy, Plus, RefreshCw, Trash2 } from 'lucide-react';
import { useCallback, useEffect, useMemo, useState } from 'react';
import { toast } from 'sonner';

import { useAuth } from '../../contexts/AuthContext';
import * as embedsApi from '../../lib/api/embeds';
import type { EmbedSummary, EmbedWithToken } from '../../lib/api/embeds';
import { Button, Callout, ModalShell } from '../ui';
import { EmbedDetailPanel } from './embeds/EmbedDetailPanel';
import { CreateEmbedDialog } from './embeds/CreateEmbedDialog';
import { TokenRevealDialog } from './embeds/TokenRevealDialog';

export function AdminEmbedsPage() {
  const { can } = useAuth();
  const [embeds, setEmbeds] = useState<EmbedSummary[]>([]);
  const [filter, setFilter] = useState('');
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [createOpen, setCreateOpen] = useState(false);
  const [revealed, setRevealed] = useState<EmbedWithToken | null>(null);
  const [snippetOpen, setSnippetOpen] = useState<EmbedSummary | null>(null);

  const allowed = can('admin.embed.manage');

  const refresh = useCallback(async () => {
    if (!allowed) return;
    setLoading(true);
    setError(null);
    try {
      const list = await embedsApi.listEmbeds();
      setEmbeds(list);
      setSelectedId((prev) => prev ?? list[0]?.id ?? null);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'errore caricamento');
    } finally {
      setLoading(false);
    }
  }, [allowed]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const filtered = useMemo(() => {
    const q = filter.trim().toLowerCase();
    if (!q) return embeds;
    return embeds.filter(
      (e) =>
        e.name.toLowerCase().includes(q) ||
        e.slug.toLowerCase().includes(q) ||
        e.origin_allowlist.some((o) => o.toLowerCase().includes(q))
    );
  }, [embeds, filter]);

  const selected = useMemo(
    () => filtered.find((e) => e.id === selectedId) ?? null,
    [filtered, selectedId]
  );

  const deleteEmbed = useCallback(
    async (e: EmbedSummary) => {
      if (!window.confirm(`Eliminare il widget "${e.name}"? Il token diventerà invalido.`)) return;
      try {
        await embedsApi.deleteEmbed(e.id);
        toast.success(`Eliminato "${e.name}"`);
        if (selectedId === e.id) setSelectedId(null);
        await refresh();
      } catch (err) {
        toast.error(err instanceof Error ? err.message : 'eliminazione fallita');
      }
    },
    [refresh, selectedId]
  );

  const rotateToken = useCallback(
    async (e: EmbedSummary) => {
      if (
        !window.confirm(
          `Ruotare il token di "${e.name}"? Il widget attualmente deployato smetterà di funzionare finché non aggiorni lo snippet.`
        )
      ) {
        return;
      }
      try {
        const result = await embedsApi.rotateToken(e.id);
        toast.success('Token ruotato — copia il nuovo plaintext');
        setRevealed(result);
        await refresh();
      } catch (err) {
        toast.error(err instanceof Error ? err.message : 'rotazione fallita');
      }
    },
    [refresh]
  );

  if (!allowed) {
    return (
      <div className="p-8">
        <Callout tone="warning">
          Permesso ``admin.embed.manage`` richiesto per gestire i widget embed.
        </Callout>
      </div>
    );
  }

  return (
    <div className="flex h-full">
      <section className="flex flex-1 flex-col min-w-0 border-r border-[var(--color-border)]">
        <div className="flex items-center gap-3 border-b border-[var(--color-border)] px-5 py-3">
          <input
            type="search"
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            placeholder="cerca per nome, slug, origine…"
            className="input-sm flex-1 max-w-md"
            aria-label="filtra embed"
          />
          <span className="text-[11px] text-ink-subtle">
            {filtered.length} / {embeds.length}
          </span>
          <div className="ml-auto">
            <Button variant="primary" size="sm" onClick={() => setCreateOpen(true)}>
              <Plus size={13} />
              Nuovo widget
            </Button>
          </div>
        </div>

        {error && (
          <Callout tone="warning" className="m-5">
            {error}
          </Callout>
        )}

        <div className="flex-1 overflow-y-auto">
          <table className="w-full border-separate border-spacing-0 text-xs">
            <thead className="sticky top-0 z-10 bg-[var(--color-canvas)] text-[10px] uppercase text-ink-subtle">
              <tr>
                <th className="px-5 py-2 text-left">Nome</th>
                <th className="px-5 py-2 text-left">Slug</th>
                <th className="px-5 py-2 text-left">Origini</th>
                <th className="px-5 py-2 text-left">Rate/min</th>
                <th className="px-5 py-2 text-left">Stato</th>
                <th className="px-5 py-2 text-left">Token</th>
                <th className="px-5 py-2"></th>
              </tr>
            </thead>
            <tbody>
              {loading && (
                <tr>
                  <td colSpan={7} className="px-5 py-8 text-center text-ink-subtle">
                    Caricamento…
                  </td>
                </tr>
              )}
              {!loading && filtered.length === 0 && (
                <tr>
                  <td colSpan={7} className="px-5 py-8 text-center text-ink-subtle">
                    Nessun widget configurato. Crea il primo con "Nuovo widget".
                  </td>
                </tr>
              )}
              {filtered.map((e) => {
                const isSel = e.id === selectedId;
                return (
                  <tr
                    key={e.id}
                    onClick={() => setSelectedId(e.id)}
                    className={
                      'cursor-pointer border-b border-[var(--color-border)] ' +
                      (isSel
                        ? 'bg-[var(--color-brand-soft)]'
                        : 'hover:bg-[var(--color-surface-hover)]')
                    }
                  >
                    <td className="px-5 py-2 font-medium">{e.name}</td>
                    <td className="px-5 py-2 font-mono text-ink-subtle">{e.slug}</td>
                    <td className="px-5 py-2 text-ink-subtle">
                      {e.origin_allowlist.length === 0
                        ? '—'
                        : `${e.origin_allowlist.length} origini`}
                    </td>
                    <td className="px-5 py-2">{e.rate_limit_per_minute}</td>
                    <td className="px-5 py-2">
                      <span
                        className={
                          'inline-block rounded px-2 py-0.5 text-[10px] font-medium ' +
                          (e.is_enabled
                            ? 'bg-emerald-100 text-emerald-700'
                            : 'bg-zinc-200 text-zinc-600')
                        }
                      >
                        {e.is_enabled ? 'attivo' : 'disattivo'}
                      </span>
                    </td>
                    <td className="px-5 py-2 font-mono text-[10px] text-ink-subtle">
                      {e.token_prefix}…
                    </td>
                    <td className="px-3 py-2 text-right">
                      <div className="flex items-center justify-end gap-1">
                        <button
                          type="button"
                          className="btn-ghost"
                          title="Copia snippet HTML"
                          onClick={(ev) => {
                            ev.stopPropagation();
                            setSnippetOpen(e);
                          }}
                          aria-label={`Snippet ${e.name}`}
                        >
                          <Copy size={12} />
                        </button>
                        <button
                          type="button"
                          className="btn-ghost"
                          title="Ruota token"
                          onClick={(ev) => {
                            ev.stopPropagation();
                            void rotateToken(e);
                          }}
                          aria-label={`Ruota token ${e.name}`}
                        >
                          <RefreshCw size={12} />
                        </button>
                        <button
                          type="button"
                          className="btn-ghost text-danger"
                          onClick={(ev) => {
                            ev.stopPropagation();
                            void deleteEmbed(e);
                          }}
                          aria-label={`Elimina ${e.name}`}
                        >
                          <Trash2 size={12} />
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </section>

      {selected && (
        <EmbedDetailPanel
          key={selected.id}
          embed={selected}
          onChanged={() => void refresh()}
        />
      )}

      <CreateEmbedDialog
        open={createOpen}
        onClose={() => setCreateOpen(false)}
        onCreated={(result) => {
          setCreateOpen(false);
          setRevealed(result);
          void refresh();
        }}
      />

      <TokenRevealDialog
        result={revealed}
        onClose={() => setRevealed(null)}
      />

      {snippetOpen && (
        <SnippetDialog embed={snippetOpen} onClose={() => setSnippetOpen(null)} />
      )}
    </div>
  );
}


function SnippetDialog({
  embed,
  onClose,
}: {
  embed: EmbedSummary;
  onClose: () => void;
}) {
  const origin = window.location.origin;
  // Il token plaintext NON è disponibile dopo la creazione; lo snippet
  // mostra un placeholder e ricorda all'admin che il token va recuperato
  // dall'evento di create/rotate.
  const snippet = `<!-- Wiki chat widget -->
<script src="${origin}/embed.js"
        data-token="<INCOLLA_TOKEN_PLAINTEXT>"
        data-position="${embed.theme.position ?? 'bottom-right'}"
        data-color="${embed.theme.primary ?? '#0ea5e9'}"
        data-label="Chat"></script>`;
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(snippet);
      toast.success('Snippet copiato');
    } catch {
      toast.error('Copia fallita — seleziona manualmente');
    }
  };
  return (
    <ModalShell open onClose={onClose} title={`Snippet HTML — ${embed.name}`} width="lg">
      <div className="space-y-3 p-1">
        <p className="text-sm text-ink-subtle">
          Incolla nel sito autorizzato (origin in allowlist). Il token plaintext si recupera
          solo dall'evento di creazione o tramite "Ruota token".
        </p>
        <pre className="rounded-md border border-[var(--color-border)] bg-zinc-50 p-3 font-mono text-[11px] leading-relaxed text-ink overflow-x-auto">
          {snippet}
        </pre>
        <div className="flex justify-end">
          <Button variant="primary" size="sm" onClick={() => void copy()}>
            <Copy size={13} />
            Copia
          </Button>
        </div>
      </div>
    </ModalShell>
  );
}
