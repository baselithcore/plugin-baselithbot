/** Org-wide "require MFA for everyone" toggle card. */

import { ShieldCheck } from 'lucide-react';
import { useTranslation } from 'react-i18next';

interface Props {
  value: boolean;
  saving: boolean;
  onToggle: () => void;
}

const MfaPolicyCard = ({ value, saving, onToggle }: Props) => {
  const { t } = useTranslation();
  return (
    <div className="mfa-card">
      <div className="mfa-info">
        <span className="mfa-ico">
          <ShieldCheck size={20} />
        </span>
        <div>
          <div className="mfa-title">{t('access.security.mfaAll')}</div>
          <div className="mfa-hint">{t('access.security.mfaAllHint')}</div>
        </div>
      </div>
      <button
        type="button"
        role="switch"
        aria-checked={value}
        aria-label={t('access.security.mfaAll')}
        disabled={saving}
        className={`switch ${value ? 'on' : ''}`}
        onClick={onToggle}
      >
        <span className="switch-knob" />
      </button>
    </div>
  );
};

export default MfaPolicyCard;
