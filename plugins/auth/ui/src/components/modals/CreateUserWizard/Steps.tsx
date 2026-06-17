/**
 * The four wizard steps: Identity, Credentials, Access, Review.
 * Pure presentational components driven by the shared WizardData state.
 */

import { Check } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { ROLES } from '../../../types';
import PasswordField from './PasswordField';
import type { StepProps } from './types';

export const IdentityStep = ({ data, update }: StepProps) => {
  const { t } = useTranslation();
  return (
    <div>
      <h3 className="wz-step-title">{t('wizard.identity.title')}</h3>
      <p className="wz-step-hint">{t('wizard.identity.hint')}</p>

      <div className="admin-form-group">
        <label className="admin-label">{t('modals.fields.emailAddress')}</label>
        <input
          type="email"
          className="admin-input"
          value={data.email}
          onChange={(e) => update('email', e.target.value)}
          placeholder={t('modals.placeholders.email')}
          autoFocus
        />
      </div>

      <div className="admin-form-group">
        <label className="admin-label">{t('modals.fields.usernameOptional')}</label>
        <input
          type="text"
          className="admin-input"
          value={data.username}
          onChange={(e) => update('username', e.target.value)}
          placeholder={t('modals.placeholders.username')}
        />
      </div>
    </div>
  );
};

export const CredentialsStep = ({ data, update }: StepProps) => {
  const { t } = useTranslation();
  return (
    <div>
      <h3 className="wz-step-title">{t('wizard.credentials.title')}</h3>
      <p className="wz-step-hint">{t('wizard.credentials.hint')}</p>
      <PasswordField
        autoGenerate={data.autoGenerate}
        onAutoGenerateChange={(v) => update('autoGenerate', v)}
        password={data.password}
        onPasswordChange={(v) => update('password', v)}
      />
    </div>
  );
};

export const AccessStep = ({ data, update, availableTabs }: StepProps) => {
  const { t } = useTranslation();
  const isGuest = data.roles.includes('guest');

  const toggle = <K extends 'roles' | 'allowedTabs'>(key: K, value: string) => {
    const list = data[key];
    update(key, list.includes(value) ? list.filter((v) => v !== value) : [...list, value]);
  };

  return (
    <div>
      <h3 className="wz-step-title">{t('wizard.access.title')}</h3>
      <p className="wz-step-hint">{t('wizard.access.hint')}</p>

      <label className="admin-label">{t('modals.fields.roles')}</label>
      <div className="wz-choice-grid">
        {ROLES.map((role) => {
          const selected = data.roles.includes(role);
          return (
            <button
              key={role}
              type="button"
              className={`wz-choice ${selected ? 'selected' : ''}`}
              onClick={() => toggle('roles', role)}
            >
              <Check size={15} className="wz-choice-check" style={{ opacity: selected ? 1 : 0 }} />
              <span>
                <span className="wz-choice-name">{t(`wizard.roles.${role}.name`)}</span>
                <span className="wz-choice-desc">{t(`wizard.roles.${role}.desc`)}</span>
              </span>
            </button>
          );
        })}
      </div>

      {isGuest && (
        <div style={{ marginTop: '1rem' }}>
          <label className="admin-label">{t('modals.fields.allowedTabs')}</label>
          {availableTabs.length > 0 ? (
            <div className="wz-choice-grid">
              {availableTabs.map((tab) => {
                const selected = data.allowedTabs.includes(tab.id);
                return (
                  <button
                    key={tab.id}
                    type="button"
                    className={`wz-choice ${selected ? 'selected' : ''}`}
                    onClick={() => toggle('allowedTabs', tab.id)}
                  >
                    <Check
                      size={15}
                      className="wz-choice-check"
                      style={{ opacity: selected ? 1 : 0 }}
                    />
                    <span>
                      <span className="wz-choice-name">{tab.label}</span>
                      <span className="wz-choice-desc">{tab.plugin}</span>
                    </span>
                  </button>
                );
              })}
            </div>
          ) : (
            <p className="wz-step-hint">{t('modals.noPluginTabs')}</p>
          )}
          <p className="admin-form-hint">{t('modals.allowedTabsHint')}</p>
        </div>
      )}
    </div>
  );
};

export const ReviewStep = ({ data }: StepProps) => {
  const { t } = useTranslation();
  const isGuest = data.roles.includes('guest');
  return (
    <div>
      <h3 className="wz-step-title">{t('wizard.review.title')}</h3>
      <p className="wz-step-hint">{t('wizard.review.hint')}</p>

      <div className="wz-summary">
        <div className="wz-summary-row">
          <span className="wz-summary-key">{t('modals.fields.emailAddress')}</span>
          <span className="wz-summary-val">{data.email || '—'}</span>
        </div>
        <div className="wz-summary-row">
          <span className="wz-summary-key">{t('modals.fields.usernameOptional')}</span>
          <span className="wz-summary-val">{data.username || '—'}</span>
        </div>
        <div className="wz-summary-row">
          <span className="wz-summary-key">{t('wizard.review.password')}</span>
          <span className="wz-summary-val">
            {data.autoGenerate ? t('wizard.review.autoGenerated') : t('wizard.review.manual')}
          </span>
        </div>
        <div className="wz-summary-row">
          <span className="wz-summary-key">{t('modals.fields.roles')}</span>
          <span className="wz-summary-val">
            {data.roles.map((r) => (
              <span key={r} className="wz-pill">
                {r}
              </span>
            ))}
          </span>
        </div>
        {isGuest && (
          <div className="wz-summary-row">
            <span className="wz-summary-key">{t('modals.fields.allowedTabs')}</span>
            <span className="wz-summary-val">{data.allowedTabs.length || 0}</span>
          </div>
        )}
      </div>
    </div>
  );
};
