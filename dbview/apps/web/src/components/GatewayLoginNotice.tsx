import { ShieldCheck } from 'lucide-react';

/**
 * Shown instead of the local LoginPage when the app runs in gateway (central
 * SSO) mode and no central session token is present. The host console owns
 * the sign-in flow; once its token lands in localStorage the storage listener
 * in lib/auth.ts re-resolves the session automatically — no reload needed.
 *
 * Copy is bilingual (en + it) following the host platform's i18n baseline;
 * the locale is picked from the browser, falling back to English.
 */
const COPY = {
  en: {
    title: 'Sign in from the platform console',
    body: 'DBView uses your organisation’s central account. Sign in from the main console; this page unlocks automatically once your session is active.',
    action: 'Go to the console',
  },
  it: {
    title: 'Accedi dalla console della piattaforma',
    body: 'DBView usa l’account centrale della tua organizzazione. Accedi dalla console principale; questa pagina si sbloccherà automaticamente quando la sessione sarà attiva.',
    action: 'Vai alla console',
  },
} as const;

function pickLocale(): keyof typeof COPY {
  if (typeof navigator !== 'undefined' && navigator.language.toLowerCase().startsWith('it')) {
    return 'it';
  }
  return 'en';
}

export function GatewayLoginNotice() {
  const t = COPY[pickLocale()];
  return (
    <div className="h-screen w-screen flex items-center justify-center bg-surface-0">
      <div className="panel max-w-md w-full mx-4 p-8 flex flex-col items-center text-center gap-4">
        <ShieldCheck className="w-8 h-8 text-accent" aria-hidden="true" />
        <h1 className="text-[18px] font-semibold text-text">{t.title}</h1>
        <p className="text-[13px] text-text-muted leading-relaxed">{t.body}</p>
        <a href="/" className="btn btn-primary mt-2">
          {t.action}
        </a>
      </div>
    </div>
  );
}
