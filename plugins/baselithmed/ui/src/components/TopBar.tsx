import { ShieldCheck, Wifi, WifiOff } from 'lucide-react';
import { Logo } from './Logo';
import { ThemeToggle } from './ThemeToggle';

interface Props {
  pseudonym: string | null;
  sessionId: string | null;
  turns: number;
  online: boolean;
}

export function TopBar({ pseudonym, sessionId, turns, online }: Props) {
  return (
    <header
      className="sticky top-0 z-30 border-b border-ink-200/60 bg-surface-base/85 backdrop-blur-xl dark:border-ink-700/60 dark:bg-surface-dark-base/80"
      role="banner"
    >
      <div className="mx-auto flex max-w-[1480px] flex-wrap items-center justify-between gap-3 px-5 py-3 md:px-7">
        <div className="flex items-center gap-5">
          <Logo />
          <span className="hidden h-7 w-px bg-ink-200/80 dark:bg-ink-700/60 md:block" />
          <nav
            aria-label="breadcrumb"
            className="hidden items-center gap-2 text-xs text-ink-400 md:flex"
          >
            <span>Workspace</span>
            <span aria-hidden>/</span>
            <span className="font-medium text-ink-600 dark:text-ink-200">Triage Sessione</span>
          </nav>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <SessionTelemetry pseudonym={pseudonym} sessionId={sessionId} turns={turns} />
          <ConnectivityPill online={online} />
          <span className="pill-accent">
            <ShieldCheck className="h-3 w-3" aria-hidden />
            HITL attivo
          </span>
          <ThemeToggle />
        </div>
      </div>
    </header>
  );
}

function SessionTelemetry({
  pseudonym,
  sessionId,
  turns,
}: {
  pseudonym: string | null;
  sessionId: string | null;
  turns: number;
}) {
  return (
    <div className="hidden items-center gap-2 sm:flex">
      {pseudonym && (
        <span className="pill" aria-label="Paziente pseudonimizzato">
          <span className="h-1.5 w-1.5 rounded-full bg-accent-500" aria-hidden />
          {pseudonym}
        </span>
      )}
      {sessionId && (
        <span className="pill-mono" aria-label="Sessione">
          #{sessionId.slice(0, 8)}
        </span>
      )}
      <span className="pill num" aria-label={`Turni: ${turns}`}>
        {turns} turni
      </span>
    </div>
  );
}

function ConnectivityPill({ online }: { online: boolean }) {
  if (online) {
    return (
      <span className="pill" title="Connessione attiva">
        <Wifi className="h-3 w-3 text-accent-500" aria-hidden />
        Online
      </span>
    );
  }
  return (
    <span className="pill text-triage-red" title="Connessione assente">
      <WifiOff className="h-3 w-3" aria-hidden />
      Offline
    </span>
  );
}
