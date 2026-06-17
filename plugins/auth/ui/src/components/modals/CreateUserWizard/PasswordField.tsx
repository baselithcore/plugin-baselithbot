/**
 * Credentials field for the wizard: auto-generate toggle, reveal, copy, and a
 * live strength meter.
 */

import { useMemo, useState } from 'react';
import { Eye, EyeOff, RefreshCw, Copy, Check } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { generatePassword, scorePassword, STRENGTH_COLORS } from './password';

interface Props {
  autoGenerate: boolean;
  onAutoGenerateChange: (v: boolean) => void;
  password: string;
  onPasswordChange: (v: string) => void;
}

const PasswordField = ({
  autoGenerate,
  onAutoGenerateChange,
  password,
  onPasswordChange,
}: Props) => {
  const { t } = useTranslation();
  const [reveal, setReveal] = useState(false);
  const [copied, setCopied] = useState(false);

  const strength = useMemo(() => scorePassword(password), [password]);

  const copy = async () => {
    if (!password) return;
    await navigator.clipboard.writeText(password);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };

  return (
    <div>
      <label className="admin-checkbox-label" style={{ marginBottom: '0.75rem' }}>
        <input
          type="checkbox"
          checked={autoGenerate}
          onChange={(e) => onAutoGenerateChange(e.target.checked)}
        />
        {t('wizard.credentials.autoGenerate')}
      </label>

      {!autoGenerate && (
        <>
          <div className="wz-pw-row">
            <input
              type={reveal ? 'text' : 'password'}
              className="admin-input"
              value={password}
              onChange={(e) => onPasswordChange(e.target.value)}
              placeholder={t('wizard.credentials.passwordPlaceholder')}
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
            <button
              type="button"
              className="admin-btn admin-btn-secondary admin-btn-icon"
              onClick={copy}
              disabled={!password}
              title={t('wizard.credentials.copy')}
            >
              {copied ? <Check size={16} /> : <Copy size={16} />}
            </button>
            <button
              type="button"
              className="admin-btn admin-btn-secondary admin-btn-icon"
              onClick={() => onPasswordChange(generatePassword())}
              title={t('wizard.credentials.generate')}
            >
              <RefreshCw size={16} />
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
        </>
      )}
    </div>
  );
};

export default PasswordField;
