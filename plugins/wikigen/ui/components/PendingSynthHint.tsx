import { useEffect, useState } from 'react';
import { Hint } from './ui';

interface Pending {
  pack: string;
  msg: string;
}

const STORAGE_KEY = 'onboarding.pending_synth_warning';

/**
 * Surfaces the prompt-synthesis warning emitted by `scaffold_pack` once the
 * server restarts and the wizard unmounts. Read-once: clears localStorage on
 * mount, then renders a dismissible Hint keyed by pack name so further visits
 * stay quiet after the user acknowledges.
 */
export function PendingSynthHint() {
  const [pending, setPending] = useState<Pending | null>(null);

  useEffect(() => {
    try {
      const raw = window.localStorage.getItem(STORAGE_KEY);
      if (!raw) return;
      window.localStorage.removeItem(STORAGE_KEY);
      const parsed = JSON.parse(raw);
      if (parsed && typeof parsed.pack === 'string' && typeof parsed.msg === 'string') {
        setPending({ pack: parsed.pack, msg: parsed.msg });
      }
    } catch {
      /* ignore */
    }
  }, []);

  if (!pending) return null;

  return (
    <div className="px-4 sm:px-6 pt-3">
      <Hint
        id={`wizard.synth_warning.${pending.pack}`}
        tone="warning"
        title="Prompt non personalizzato"
      >
        Sintesi del prompt fallita ({pending.msg}). Sono stati usati i prompt
        generici di <code>_template</code>. Modifica{' '}
        <code>domains/{pending.pack}/prompts/system.j2</code> per affinare le
        risposte sul tuo dominio.
      </Hint>
    </div>
  );
}
