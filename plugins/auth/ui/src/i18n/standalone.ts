/**
 * Standalone translator for the *shared* auth components (LoginPage,
 * ProtectedRoute).
 *
 * These components are consumed cross-plugin via the `@auth` alias. Binding
 * them to `react-i18next` forced every consuming plugin to install + initialize
 * i18next just to render the shared login wall — which silently broke the build
 * of every consumer that didn't (most of them). To keep the shared auth UI
 * truly self-contained, it carries its own tiny en/it catalog with zero
 * external dependencies. The auth plugin's own app keeps using react-i18next
 * for the rest of its surface.
 *
 * Locale resolution order: persisted `i18nextLng`/`lang` -> navigator language
 * -> `en` (fallback). en + it kept in parity (project i18n rule).
 */

type Catalog = Record<string, string>;

const EN: Catalog = {
  'login.brandSubtitle': 'Sign in to access the system',
  'login.identifier': 'Email or username',
  'login.identifierPlaceholderCombined': 'you@example.com or username',
  'login.password': 'Password',
  'login.passwordDots': '••••••••',
  'login.submit': 'Sign in',
  'login.or': 'or',
  'login.passkey': 'Sign in with a passkey',
  'login.ssoContinue': 'Continue with {{name}}',
  'login.ssoError': 'Single sign-on failed. Please try again or use another method.',
  'login.forgotPassword': 'Forgot your password?',
  'login.footer': '© 2026 Gippo. All rights reserved.',
  'login.mfaHeader': 'Two-Factor Authentication',
  'login.mfaHeaderSubtitle': 'Enter the code from your authenticator app',
  'login.mfaCodeLabel': 'Verification Code',
  'login.mfaCodePlaceholder': '000000',
  'login.mfaCodeHint': 'Enter your 6-digit code or a backup code',
  'login.verify': 'Verify',
  'login.backToLogin': 'Back to login',
  'login.errors.loginFailed': 'Login failed',
  'login.errors.missingMfaToken': 'Missing MFA token',
  'login.errors.mfaVerificationFailed': 'MFA verification failed',
  'protected.loading': 'Loading...',
  'protected.accessDenied': 'Access Denied',
  'protected.noPagePermission': "You don't have permission to access this page.",
  'protected.noSectionAccess': "You don't have access to this section.",
  'protected.requiredRole': 'Required role:',
  'protected.limitedTo': 'Your access is limited to: {{tabs}}',
};

const IT: Catalog = {
  'login.brandSubtitle': 'Accedi per utilizzare il sistema',
  'login.identifier': 'Email o nome utente',
  'login.identifierPlaceholderCombined': 'tu@esempio.com o nome utente',
  'login.password': 'Password',
  'login.passwordDots': '••••••••',
  'login.submit': 'Accedi',
  'login.or': 'oppure',
  'login.passkey': 'Accedi con una passkey',
  'login.ssoContinue': 'Continua con {{name}}',
  'login.ssoError': 'Accesso SSO non riuscito. Riprova o usa un altro metodo.',
  'login.forgotPassword': 'Password dimenticata?',
  'login.footer': '© 2026 Gippo. Tutti i diritti riservati.',
  'login.mfaHeader': 'Autenticazione a due fattori',
  'login.mfaHeaderSubtitle': 'Inserisci il codice dalla tua app di autenticazione',
  'login.mfaCodeLabel': 'Codice di verifica',
  'login.mfaCodePlaceholder': '000000',
  'login.mfaCodeHint': 'Inserisci il codice a 6 cifre o un codice di backup',
  'login.verify': 'Verifica',
  'login.backToLogin': "Torna all'accesso",
  'login.errors.loginFailed': 'Accesso non riuscito',
  'login.errors.missingMfaToken': 'Token MFA mancante',
  'login.errors.mfaVerificationFailed': 'Verifica MFA non riuscita',
  'protected.loading': 'Caricamento...',
  'protected.accessDenied': 'Accesso negato',
  'protected.noPagePermission': 'Non hai il permesso di accedere a questa pagina.',
  'protected.noSectionAccess': 'Non hai accesso a questa sezione.',
  'protected.requiredRole': 'Ruolo richiesto:',
  'protected.limitedTo': 'Il tuo accesso è limitato a: {{tabs}}',
};

const CATALOGS: Record<string, Catalog> = { en: EN, it: IT };

function resolveLang(): 'en' | 'it' {
  try {
    const stored = localStorage.getItem('i18nextLng') || localStorage.getItem('lang') || '';
    const nav = typeof navigator !== 'undefined' ? navigator.language : '';
    const lang = (stored || nav || 'en').slice(0, 2).toLowerCase();
    return lang === 'it' ? 'it' : 'en';
  } catch {
    return 'en';
  }
}

export type StandaloneT = (key: string, vars?: Record<string, string>) => string;

/**
 * Returns a `t(key, vars?)` function. `{{var}}` placeholders are interpolated.
 * Missing keys fall back to English, then to the key itself.
 */
export function useAuthT(): StandaloneT {
  const catalog = CATALOGS[resolveLang()] ?? EN;
  return (key: string, vars?: Record<string, string>): string => {
    let value = catalog[key] ?? EN[key] ?? key;
    if (vars) {
      for (const [name, replacement] of Object.entries(vars)) {
        value = value.replace(new RegExp(`{{\\s*${name}\\s*}}`, 'g'), replacement);
      }
    }
    return value;
  };
}
