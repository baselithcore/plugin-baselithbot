import { AlertTriangle, BookOpenCheck, Loader2, ShieldCheck } from 'lucide-react';
import { useEffect, useState } from 'react';
import { toast } from 'sonner';
import {
  type ObsidianStateResponse,
  disableObsidian,
  fetchObsidianState,
  initObsidian,
} from '../../lib/api/admin';
import { Button } from '../ui';

interface Props {
  tenant: string;
}

/**
 * Pannello admin per gestire l'integrazione Obsidian sul tenant attivo.
 *
 * Dual-key gate: questo bottone seeda `.obsidian/` (con preview-mode di
 * default) e marca il vault come Obsidian-enabled. Lato utente finale è
 * comunque richiesto il permesso ``obsidian.open`` (mig 012).
 */
export function ObsidianSection({ tenant }: Props) {
  const [state, setState] = useState<ObsidianStateResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [confirmInit, setConfirmInit] = useState(false);
  const [confirmDisable, setConfirmDisable] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    fetchObsidianState(tenant)
      .then((s) => {
        if (!cancelled) setState(s);
      })
      .catch((e: Error) => {
        if (!cancelled) toast.error(`Stato Obsidian: ${e.message}`);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [tenant]);

  const handleInit = async () => {
    setBusy(true);
    try {
      const s = await initObsidian(tenant);
      setState(s);
      toast.success('Obsidian inizializzato. Apri il vault dal client desktop.');
      setConfirmInit(false);
    } catch (e) {
      toast.error(`Init fallita: ${(e as Error).message}`);
    } finally {
      setBusy(false);
    }
  };

  const handleDisable = async () => {
    setBusy(true);
    try {
      const s = await disableObsidian(tenant);
      setState(s);
      toast.success('Integrazione Obsidian disattivata.');
      setConfirmDisable(false);
    } catch (e) {
      toast.error(`Disattivazione fallita: ${(e as Error).message}`);
    } finally {
      setBusy(false);
    }
  };

  if (loading) {
    return (
      <div
        className="flex items-center gap-2 text-[11px] text-ink-subtle"
        role="status"
        aria-live="polite"
      >
        <Loader2 size={12} className="animate-spin" aria-hidden /> Controllo dello stato…
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <p className="text-[11px] leading-relaxed text-ink-muted">
        Inizializza il vault per consentire la lettura della wiki dal client Obsidian. La pipeline
        di ingest scrive in <code>wiki/</code> — gli utenti finali con il permesso{' '}
        <code>obsidian.open</code> potranno aprire le pagine ma è loro responsabilità non
        modificarle (la configurazione predefinita imposta la modalità <em>preview</em>).
      </p>

      <div className="flex items-center justify-between gap-3 rounded-md border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-2">
        <div className="flex items-center gap-2">
          {state?.enabled ? (
            <ShieldCheck size={14} className="text-[var(--color-success)]" />
          ) : (
            <AlertTriangle size={14} className="text-[var(--color-warning)]" />
          )}
          <div>
            <div className="text-xs font-medium text-ink">
              {state?.enabled ? 'Attivo' : 'Non attivo'}
            </div>
            {state?.initialized_at && (
              <div className="text-[10px] text-ink-subtle">
                inizializzato {new Date(state.initialized_at).toLocaleString('it-IT')}
                {state.initialized_by ? ` · da ${state.initialized_by.slice(0, 8)}` : ''}
              </div>
            )}
          </div>
        </div>
        {state?.enabled ? (
          confirmDisable ? (
            <div className="flex items-center gap-1.5">
              <Button
                variant="secondary"
                onClick={() => setConfirmDisable(false)}
                disabled={busy}
                className="!text-[11px]"
              >
                Annulla
              </Button>
              <Button
                variant="primary"
                onClick={handleDisable}
                disabled={busy}
                className="!text-[11px]"
              >
                {busy ? <Loader2 size={11} className="animate-spin" aria-hidden /> : null}
                Conferma
              </Button>
            </div>
          ) : (
            <Button
              variant="secondary"
              onClick={() => setConfirmDisable(true)}
              disabled={busy}
              className="!text-[11px]"
            >
              Disattiva
            </Button>
          )
        ) : confirmInit ? (
          <div className="flex items-center gap-1.5">
            <Button
              variant="secondary"
              onClick={() => setConfirmInit(false)}
              disabled={busy}
              className="!text-[11px]"
            >
              Annulla
            </Button>
            <Button variant="primary" onClick={handleInit} disabled={busy} className="!text-[11px]">
              {busy ? <Loader2 size={11} className="animate-spin" /> : <BookOpenCheck size={11} />}
              Conferma
            </Button>
          </div>
        ) : (
          <Button
            variant="primary"
            onClick={() => setConfirmInit(true)}
            disabled={busy}
            className="!text-[11px]"
          >
            <BookOpenCheck size={11} /> Inizializza
          </Button>
        )}
      </div>

      {confirmInit && !state?.enabled && (
        <div className="text-[11px] text-ink-muted bg-[var(--color-warning)]/10 border border-[var(--color-warning)]/30 rounded-md px-2.5 py-2">
          L'azione crea <code>.obsidian/</code> dentro il vault con preset read-only-friendly e
          abilita il pulsante "Apri in Obsidian" lato chat per gli utenti autorizzati. Idempotente —
          sicuro da rieseguire.
        </div>
      )}

      {confirmDisable && state?.enabled && (
        <div className="text-[11px] text-ink-muted bg-[var(--color-warning)]/10 border border-[var(--color-warning)]/30 rounded-md px-2.5 py-2">
          La disattivazione nasconde il pulsante "Apri in Obsidian" agli utenti. La cartella{' '}
          <code>.obsidian/</code> resta intatta sul disco — riattivabile in qualsiasi momento.
        </div>
      )}
    </div>
  );
}
