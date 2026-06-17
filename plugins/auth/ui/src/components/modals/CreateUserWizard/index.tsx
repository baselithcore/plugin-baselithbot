/**
 * Create-user wizard — a guided, multi-step replacement for the old single
 * CreateUserModal. Drop-in API (onClose / onCreate / isLoading).
 *
 * Steps: Identity → Credentials → Access → Review. Per-step validation gates
 * the "Next" button; the final step submits a CreateUserRequest.
 */

import { useEffect, useMemo, useState } from 'react';
import { X, ArrowLeft, ArrowRight, UserPlus } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import type { CreateUserRequest, PluginTab } from '../../../types';
import { getPluginTabs } from '../../../api/auth';
import { useAuth } from '../../../hooks/useAuthContext';
import { IdentityStep, CredentialsStep, AccessStep, ReviewStep } from './Steps';
import { INITIAL_DATA, type WizardData } from './types';
import './wizard.css';

interface Props {
  onClose: () => void;
  onCreate: (data: CreateUserRequest) => Promise<void>;
  isLoading: boolean;
}

const STEP_KEYS = ['identity', 'credentials', 'access', 'review'] as const;
const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

const CreateUserWizard = ({ onClose, onCreate, isLoading }: Props) => {
  const { t } = useTranslation();
  const { accessToken } = useAuth();
  const [step, setStep] = useState(0);
  const [data, setData] = useState<WizardData>(INITIAL_DATA);
  const [availableTabs, setAvailableTabs] = useState<PluginTab[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!accessToken) return;
    getPluginTabs(accessToken)
      .then(setAvailableTabs)
      .catch(() => {});
  }, [accessToken]);

  const update = <K extends keyof WizardData>(key: K, value: WizardData[K]) => {
    setData((d) => ({ ...d, [key]: value }));
    setError(null);
  };

  // Each step is gated by its own validity.
  const stepValid = useMemo(() => {
    switch (STEP_KEYS[step]) {
      case 'identity':
        return EMAIL_RE.test(data.email);
      case 'credentials':
        return data.autoGenerate || data.password.length >= 8;
      case 'access':
        return data.roles.length > 0;
      default:
        return true;
    }
  }, [step, data]);

  const stepProps = { data, update, availableTabs };
  const STEP_VIEWS = [IdentityStep, CredentialsStep, AccessStep, ReviewStep];
  const Current = STEP_VIEWS[step];
  const isLast = step === STEP_KEYS.length - 1;

  const next = () => {
    if (!stepValid) {
      setError(t('wizard.errors.fixStep'));
      return;
    }
    setStep((s) => Math.min(s + 1, STEP_KEYS.length - 1));
  };

  const submit = async () => {
    setError(null);
    try {
      const isGuest = data.roles.includes('guest');
      await onCreate({
        email: data.email,
        username: data.username.trim() || undefined,
        password: data.autoGenerate ? undefined : data.password,
        roles: data.roles,
        allowed_tabs: isGuest && data.allowedTabs.length > 0 ? data.allowedTabs : undefined,
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : t('modals.errors.createFailed'));
    }
  };

  return (
    <div className="admin-modal-overlay">
      <div className="admin-modal wz-modal">
        <div className="admin-modal-header">
          <h3>
            <UserPlus size={18} style={{ verticalAlign: '-3px', marginRight: '0.5rem' }} />
            {t('wizard.title')}
          </h3>
          <button onClick={onClose} className="admin-close-btn" disabled={isLoading}>
            <X size={20} />
          </button>
        </div>

        <div style={{ padding: '1rem 1.5rem 0' }}>
          <div className="wz-steps">
            {STEP_KEYS.map((key, i) => (
              <div key={key} style={{ display: 'contents' }}>
                <div className={`wz-step ${i === step ? 'active' : ''} ${i < step ? 'done' : ''}`}>
                  <span className="wz-step-dot">{i + 1}</span>
                  <span className="wz-step-label">{t(`wizard.${key}.step`)}</span>
                </div>
                {i < STEP_KEYS.length - 1 && <span className="wz-step-line" />}
              </div>
            ))}
          </div>
        </div>

        {error && <div className="admin-error-message">{error}</div>}

        <div className="admin-modal-body wz-body">
          <Current {...stepProps} />
        </div>

        <div className="admin-modal-footer wz-footer">
          {step > 0 ? (
            <button
              type="button"
              className="admin-btn admin-btn-secondary"
              onClick={() => setStep((s) => s - 1)}
              disabled={isLoading}
            >
              <ArrowLeft size={16} />
              {t('common.back')}
            </button>
          ) : (
            <span />
          )}

          <div className="wz-footer-right">
            <button
              type="button"
              className="admin-btn admin-btn-ghost"
              onClick={onClose}
              disabled={isLoading}
            >
              {t('common.cancel')}
            </button>
            {isLast ? (
              <button
                type="button"
                className="admin-btn admin-btn-primary"
                onClick={submit}
                disabled={isLoading}
              >
                {isLoading ? <span className="admin-spinner" /> : t('wizard.submit')}
              </button>
            ) : (
              <button
                type="button"
                className="admin-btn admin-btn-primary"
                onClick={next}
                disabled={!stepValid}
              >
                {t('common.next')}
                <ArrowRight size={16} />
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default CreateUserWizard;
