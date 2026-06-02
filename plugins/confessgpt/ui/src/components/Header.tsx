import { Cross, Lock } from 'lucide-react';

export function Header() {
  return (
    <header className="flex items-center justify-between gap-4 border-b border-gold-subtle pb-3">
      <div className="flex items-center gap-3">
        <Cross
          className="h-9 w-9 text-gold-bright drop-shadow-[0_0_10px_rgba(201,168,106,0.35)]"
          strokeWidth={1.6}
        />
        <div>
          <div className="font-serif text-2xl font-medium tracking-wide text-parchment">
            ConfessGPT
          </div>
          <div className="mt-0.5 text-[0.65rem] uppercase tracking-[0.32em] text-ash">
            Rito Romano · CEI
          </div>
        </div>
      </div>

      <div
        role="status"
        aria-live="polite"
        title="Sigillum sacramentale — nulla di quanto confessi viene registrato, salvato o trasmesso. La sessione esiste solo in memoria volatile e viene cancellata al termine del rito."
        className="inline-flex items-center gap-2 rounded-full border border-gold-medium bg-surface-2 px-3 py-1.5 text-[0.65rem] font-medium uppercase tracking-[0.18em] text-gold-bright backdrop-blur-md transition-colors hover:border-gold-strong hover:bg-surface-3"
      >
        <span
          className="h-1.5 w-1.5 animate-pulse rounded-full bg-gold-bright shadow-[0_0_8px_#c9a86a]"
          aria-hidden
        />
        <Lock className="h-3 w-3" strokeWidth={1.8} aria-hidden />
        Sigillum
      </div>
    </header>
  );
}
