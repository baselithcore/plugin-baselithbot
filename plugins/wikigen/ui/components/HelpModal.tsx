import { Keyboard } from 'lucide-react';
import { useMemo } from 'react';

import { useAuth } from '../contexts/AuthContext';
import { ModalShell, SectionHeader } from './ui';

interface Props {
  open: boolean;
  onClose: () => void;
}

interface Shortcut {
  keys: string[];
  label: string;
  /** Permesso richiesto per esporre lo shortcut. Omesso = sempre visibile.
   *  Le scorciatoie filtrate qui sono anche no-op a livello globale in
   *  ``App.tsx`` (handler gated da ``can(...)``) — questa modal mostra
   *  quindi solo quelle effettivamente operative per l'utente corrente. */
  perm?: string;
}

const SHORTCUTS: { group: string; items: Shortcut[] }[] = [
  {
    group: 'Conversazione',
    items: [
      { keys: ['⌘', 'K'], label: 'Nuova conversazione', perm: 'conversation.write' },
      { keys: ['⌘', 'B'], label: 'Mostra/nascondi sidebar' },
      { keys: ['⌘', '/'], label: 'Apri tavolozza comandi', perm: 'view.command_palette' },
      { keys: ['⌘', ','], label: 'Apri impostazioni', perm: 'view.settings' },
      { keys: ['⌘', 'U'], label: 'Carica documento', perm: 'ingest.run' },
      { keys: ['?'], label: 'Apri questa guida', perm: 'view.help' },
    ],
  },
  {
    group: 'Composer',
    items: [
      { keys: ['↵'], label: 'Invia messaggio' },
      { keys: ['⇧', '↵'], label: 'A capo senza inviare' },
      { keys: ['Esc'], label: 'Interrompi generazione' },
    ],
  },
  {
    group: 'Modifica messaggi',
    items: [
      { keys: ['⌘', '↵'], label: 'Salva e rigenera (in modifica)' },
      { keys: ['Esc'], label: 'Annulla modifica' },
      {
        keys: ['dbl click'],
        label: 'Rinomina conversazione in sidebar',
        perm: 'conversation.write',
      },
    ],
  },
  {
    group: 'Tavolozza comandi',
    items: [
      { keys: ['↑', '↓'], label: 'Naviga risultati' },
      { keys: ['↵'], label: 'Esegui comando selezionato' },
      { keys: ['Esc'], label: 'Chiudi tavolozza' },
    ],
    // Tutto il gruppo dipende da view.command_palette; filtrato dinamicamente.
  },
];

export function HelpModal({ open, onClose }: Props) {
  const { can } = useAuth();

  const visibleGroups = useMemo(() => {
    return SHORTCUTS.map((g) => ({
      group: g.group,
      items: g.items.filter((s) => !s.perm || can(s.perm)),
    }))
      .filter((g) => g.items.length > 0)
      .filter((g) => g.group !== 'Tavolozza comandi' || can('view.command_palette'));
  }, [can]);

  return (
    <ModalShell
      open={open}
      onClose={onClose}
      title="Scorciatoie da tastiera"
      icon={Keyboard}
      width="lg"
    >
      <div className="max-h-[70vh] overflow-y-auto px-5 py-4">
        {visibleGroups.map((g) => (
          <section key={g.group} className="mb-4 last:mb-0">
            <SectionHeader title={g.group} />
            <ul className="flex flex-col gap-1.5">
              {g.items.map((s, i) => (
                <li
                  key={i}
                  className="flex items-center justify-between gap-3 rounded-md px-2 py-1.5 hover:bg-[var(--color-surface)]"
                >
                  <span className="text-xs text-ink-muted">{s.label}</span>
                  <span className="flex shrink-0 items-center gap-1">
                    {s.keys.map((k, j) => (
                      <kbd
                        key={j}
                        className="inline-flex items-center rounded border border-[var(--color-border)] bg-[var(--color-surface)]
                                   px-1.5 py-0.5 font-mono text-[10px] text-ink"
                      >
                        {k}
                      </kbd>
                    ))}
                  </span>
                </li>
              ))}
            </ul>
          </section>
        ))}
      </div>
    </ModalShell>
  );
}
