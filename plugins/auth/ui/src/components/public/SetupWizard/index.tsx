/**
 * First-run setup wizard: provisions the initial admin on a fresh install.
 *
 * Flow: welcome → credentials (creates the admin + logs in) → mandatory MFA
 * enrollment → done. The created access token is stored the same way the auth
 * context stores it (localStorage 'auth_access_token'), so finishing reloads
 * straight into the authenticated admin console.
 */

import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import AuthShell from '../AuthShell';
import { initializeAdmin } from '../../../api/setup';
import { setupMFA, enableMFA, type MFASetupResponse } from '../../../api/auth';
import { CredentialsStep, DoneStep, MfaStep, WelcomeStep } from './steps';
import './setup.css';

type Step = 'welcome' | 'credentials' | 'mfa' | 'done';
const ORDER: Step[] = ['welcome', 'credentials', 'mfa', 'done'];

const TOKEN_KEY = 'auth_access_token';
const TOKEN_EXPIRY_KEY = 'auth_token_expiry';

function storeToken(token: string, expiresIn: number) {
  localStorage.setItem(TOKEN_KEY, token);
  localStorage.setItem(TOKEN_EXPIRY_KEY, (Date.now() + expiresIn * 1000).toString());
}

interface Props {
  onComplete: () => void;
}

export default function SetupWizard({ onComplete }: Props) {
  const { t } = useTranslation();
  const [step, setStep] = useState<Step>('welcome');
  const [form, setForm] = useState({ email: '', username: '', password: '', confirm: '' });
  const [token, setToken] = useState<string | null>(null);
  const [mfa, setMfa] = useState<MFASetupResponse | null>(null);
  const [code, setCode] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const patch = (p: Partial<typeof form>) => setForm((f) => ({ ...f, ...p }));

  const submitCredentials = async () => {
    setBusy(true);
    setError(null);
    try {
      const tokenResp = await initializeAdmin({
        email: form.email.trim(),
        password: form.password,
        username: form.username.trim() || undefined,
      });
      storeToken(tokenResp.access_token, tokenResp.expires_in);
      setToken(tokenResp.access_token);
      const mfaResp = await setupMFA(tokenResp.access_token);
      setMfa(mfaResp);
      setStep('mfa');
    } catch (e) {
      setError(e instanceof Error ? e.message : t('setup.errors.generic'));
    } finally {
      setBusy(false);
    }
  };

  const verifyMfa = async () => {
    if (!token) return;
    setBusy(true);
    setError(null);
    try {
      await enableMFA(token, code.trim());
      setStep('done');
    } catch (e) {
      setError(e instanceof Error ? e.message : t('setup.errors.invalidCode'));
    } finally {
      setBusy(false);
    }
  };

  const activeIndex = ORDER.indexOf(step);

  return (
    <AuthShell title={t('setup.title')} subtitle={t('setup.subtitle')}>
      <div className="setup-progress" aria-hidden="true">
        {ORDER.map((s, i) => (
          <span
            key={s}
            className={`setup-dot ${i <= activeIndex ? 'is-active' : ''} ${
              i < activeIndex ? 'is-done' : ''
            }`}
          />
        ))}
      </div>

      {step === 'welcome' && <WelcomeStep onNext={() => setStep('credentials')} />}
      {step === 'credentials' && (
        <CredentialsStep
          email={form.email}
          username={form.username}
          password={form.password}
          confirm={form.confirm}
          onChange={patch}
          onSubmit={submitCredentials}
          busy={busy}
          error={error}
        />
      )}
      {step === 'mfa' && mfa && (
        <MfaStep
          data={mfa}
          code={code}
          onCodeChange={setCode}
          onVerify={verifyMfa}
          busy={busy}
          error={error}
        />
      )}
      {step === 'done' && <DoneStep onFinish={onComplete} />}
    </AuthShell>
  );
}
