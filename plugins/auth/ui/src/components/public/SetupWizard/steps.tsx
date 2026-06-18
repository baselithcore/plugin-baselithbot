/**
 * Presentational step bodies for the first-run setup wizard. State and side
 * effects live in the orchestrator (./index.tsx); these are pure-ish views.
 */

import { useMemo, useState } from 'react';
import { Eye, EyeOff, ShieldCheck, KeyRound, Rocket, Copy, Check } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { scorePassword, STRENGTH_COLORS } from '../../modals/CreateUserWizard/password';
import type { MFASetupResponse } from '../../../api/auth';

export function WelcomeStep({ onNext }: { onNext: () => void }) {
  const { t } = useTranslation();
  return (
    <div className="setup-step">
      <div className="setup-hero-icon">
        <ShieldCheck size={40} />
      </div>
      <p className="setup-lead">{t('setup.welcome.lead')}</p>
      <ul className="setup-points">
        <li>{t('setup.welcome.point1')}</li>
        <li>{t('setup.welcome.point2')}</li>
        <li>{t('setup.welcome.point3')}</li>
      </ul>
      <button type="button" className="admin-btn admin-btn-primary setup-cta" onClick={onNext}>
        {t('setup.welcome.start')}
      </button>
    </div>
  );
}

interface CredentialsProps {
  email: string;
  username: string;
  password: string;
  confirm: string;
  onChange: (patch: Partial<Record<'email' | 'username' | 'password' | 'confirm', string>>) => void;
  onSubmit: () => void;
  busy: boolean;
  error: string | null;
}

export function CredentialsStep(props: CredentialsProps) {
  const { email, username, password, confirm, onChange, onSubmit, busy, error } = props;
  const { t } = useTranslation();
  const [reveal, setReveal] = useState(false);
  const strength = useMemo(() => scorePassword(password), [password]);
  const mismatch = confirm.length > 0 && confirm !== password;
  const canSubmit = !busy && email.includes('@') && password.length >= 8 && password === confirm;

  return (
    <form
      className="setup-step"
      onSubmit={(e) => {
        e.preventDefault();
        if (canSubmit) onSubmit();
      }}
    >
      <label className="admin-label">{t('setup.credentials.email')}</label>
      <input
        type="email"
        className="admin-input"
        value={email}
        onChange={(e) => onChange({ email: e.target.value })}
        placeholder={t('setup.credentials.emailPlaceholder')}
        autoComplete="username"
        autoFocus
      />

      <label className="admin-label">{t('setup.credentials.username')}</label>
      <input
        type="text"
        className="admin-input"
        value={username}
        onChange={(e) => onChange({ username: e.target.value })}
        placeholder={t('setup.credentials.usernamePlaceholder')}
        autoComplete="off"
      />

      <label className="admin-label">{t('setup.credentials.password')}</label>
      <div className="wz-pw-row">
        <input
          type={reveal ? 'text' : 'password'}
          className="admin-input"
          value={password}
          onChange={(e) => onChange({ password: e.target.value })}
          placeholder={t('setup.credentials.passwordPlaceholder')}
          autoComplete="new-password"
        />
        <button
          type="button"
          className="admin-btn admin-btn-secondary admin-btn-icon"
          onClick={() => setReveal((r) => !r)}
          title={t(reveal ? 'wizard.credentials.hide' : 'wizard.credentials.reveal')}
        >
          {reveal ? <EyeOff size={16} /> : <Eye size={16} />}
        </button>
      </div>

      <div className="wz-strength">
        <div className="wz-strength-track">
          {[0, 1, 2, 3].map((i) => (
            <span
              key={i}
              className="wz-strength-seg"
              style={{
                background:
                  password && i < strength.score ? STRENGTH_COLORS[strength.level] : undefined,
              }}
            />
          ))}
        </div>
        {password && (
          <div className="wz-strength-label" style={{ color: STRENGTH_COLORS[strength.level] }}>
            {t(`wizard.credentials.strength.${strength.level}`)}
          </div>
        )}
      </div>

      <label className="admin-label">{t('setup.credentials.confirm')}</label>
      <input
        type={reveal ? 'text' : 'password'}
        className="admin-input"
        value={confirm}
        onChange={(e) => onChange({ confirm: e.target.value })}
        placeholder={t('setup.credentials.confirmPlaceholder')}
        autoComplete="new-password"
      />
      {mismatch && <div className="setup-error">{t('setup.credentials.mismatch')}</div>}
      {error && <div className="setup-error">{error}</div>}

      <button type="submit" className="admin-btn admin-btn-primary setup-cta" disabled={!canSubmit}>
        {busy ? t('setup.credentials.creating') : t('setup.credentials.continue')}
      </button>
    </form>
  );
}

interface MfaProps {
  data: MFASetupResponse;
  code: string;
  onCodeChange: (v: string) => void;
  onVerify: () => void;
  busy: boolean;
  error: string | null;
}

export function MfaStep({ data, code, onCodeChange, onVerify, busy, error }: MfaProps) {
  const { t } = useTranslation();
  const [copied, setCopied] = useState(false);

  const copyCodes = async () => {
    await navigator.clipboard.writeText(data.backup_codes.join('\n'));
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };

  return (
    <form
      className="setup-step"
      onSubmit={(e) => {
        e.preventDefault();
        if (!busy && code.trim().length >= 6) onVerify();
      }}
    >
      <div className="setup-hero-icon">
        <KeyRound size={36} />
      </div>
      <p className="setup-lead">{t('setup.mfa.lead')}</p>

      {data.qr_code ? (
        <img className="setup-qr" src={data.qr_code} alt={t('setup.mfa.qrAlt')} />
      ) : (
        <div className="setup-secret-box">
          <span className="setup-secret-label">{t('setup.mfa.secret')}</span>
          <code className="setup-secret">{data.secret}</code>
        </div>
      )}

      <div className="setup-backup">
        <div className="setup-backup-head">
          <span>{t('setup.mfa.backupTitle')}</span>
          <button
            type="button"
            className="admin-btn admin-btn-secondary admin-btn-icon"
            onClick={copyCodes}
          >
            {copied ? <Check size={14} /> : <Copy size={14} />}
          </button>
        </div>
        <div className="setup-backup-grid">
          {data.backup_codes.map((c) => (
            <code key={c}>{c}</code>
          ))}
        </div>
      </div>

      <label className="admin-label">{t('setup.mfa.codeLabel')}</label>
      <input
        type="text"
        inputMode="numeric"
        className="admin-input"
        value={code}
        onChange={(e) => onCodeChange(e.target.value.replace(/\D/g, '').slice(0, 8))}
        placeholder="123456"
        autoFocus
      />
      {error && <div className="setup-error">{error}</div>}

      <button
        type="submit"
        className="admin-btn admin-btn-primary setup-cta"
        disabled={busy || code.trim().length < 6}
      >
        {busy ? t('setup.mfa.verifying') : t('setup.mfa.verify')}
      </button>
    </form>
  );
}

export function DoneStep({ onFinish }: { onFinish: () => void }) {
  const { t } = useTranslation();
  return (
    <div className="setup-step setup-done">
      <div className="setup-hero-icon setup-hero-success">
        <Rocket size={40} />
      </div>
      <p className="setup-lead">{t('setup.done.lead')}</p>
      <button type="button" className="admin-btn admin-btn-primary setup-cta" onClick={onFinish}>
        {t('setup.done.enter')}
      </button>
    </div>
  );
}
