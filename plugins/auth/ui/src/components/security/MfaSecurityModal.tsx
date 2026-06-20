/**
 * Self-service MFA (TOTP) security modal.
 *
 * Enrollment flow: status → scan QR (+ manual secret) → verify 6-digit code →
 * save backup codes. Also supports disabling MFA (admin session, confirmed).
 * Wires the existing /api/auth/mfa/{setup,enable,disable} endpoints.
 */

import { useState } from 'react';
import { X, ShieldCheck, ShieldOff, Copy, Check, Download, AlertTriangle } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { setupMFA, enableMFA, disableMFA, type MFASetupResponse } from '../../api/auth';
import { useAuth } from '../../hooks/useAuthContext';
import QrCode from '../shared/QrCode';
import './mfa.css';

type Phase = 'status' | 'scan' | 'verify' | 'backup';

const MfaSecurityModal = ({ onClose }: { onClose: () => void }) => {
  const { t } = useTranslation();
  const { user, accessToken, refreshAuth } = useAuth();
  const enabled = !!user?.mfa_enabled;

  const [phase, setPhase] = useState<Phase>('status');
  const [setup, setSetup] = useState<MFASetupResponse | null>(null);
  const [code, setCode] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  const run = async (fn: () => Promise<void>) => {
    setBusy(true);
    setError(null);
    try {
      await fn();
    } catch (err) {
      setError(err instanceof Error ? err.message : t('security.mfa.errors.generic'));
    } finally {
      setBusy(false);
    }
  };

  const beginEnroll = () =>
    run(async () => {
      if (!accessToken) return;
      const res = await setupMFA(accessToken);
      setSetup(res);
      setPhase('scan');
    });

  const verify = () =>
    run(async () => {
      if (!accessToken) return;
      await enableMFA(accessToken, code.trim());
      await refreshAuth();
      setPhase('backup');
    });

  const disable = () =>
    run(async () => {
      if (!accessToken) return;
      await disableMFA(accessToken);
      await refreshAuth();
      onClose();
    });

  const copyCodes = async () => {
    if (!setup) return;
    await navigator.clipboard.writeText(setup.backup_codes.join('\n'));
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };

  const downloadCodes = () => {
    if (!setup) return;
    const blob = new Blob([setup.backup_codes.join('\n')], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'baselith-backup-codes.txt';
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="admin-modal-overlay">
      <div className="admin-modal mfa-modal">
        <div className="admin-modal-header">
          <h3>
            <ShieldCheck size={18} style={{ verticalAlign: '-3px', marginRight: '0.5rem' }} />
            {t('security.mfa.title')}
          </h3>
          <button onClick={onClose} className="admin-close-btn" disabled={busy}>
            <X size={20} />
          </button>
        </div>

        {error && <div className="admin-error-message">{error}</div>}

        <div className="admin-modal-body">
          {phase === 'status' && (
            <div className="mfa-status">
              <span className={`mfa-status-icon ${enabled ? 'on' : 'off'}`}>
                {enabled ? <ShieldCheck size={20} /> : <ShieldOff size={20} />}
              </span>
              <div className="mfa-status-text">
                <div className="mfa-status-title">
                  {t(enabled ? 'security.mfa.enabledTitle' : 'security.mfa.disabledTitle')}
                </div>
                <div className="mfa-status-sub">
                  {t(enabled ? 'security.mfa.enabledSub' : 'security.mfa.disabledSub')}
                </div>
              </div>
            </div>
          )}

          {phase === 'scan' && setup && (
            <div className="mfa-qr-wrap">
              <p className="wz-step-hint" style={{ marginBottom: 0 }}>
                {t('security.mfa.scanHint')}
              </p>
              <QrCode
                className="mfa-qr"
                src={setup.qr_code}
                value={setup.provisioning_uri}
                alt={t('security.mfa.qrAlt')}
              />
              <div className="mfa-secret">{setup.secret}</div>
            </div>
          )}

          {phase === 'verify' && (
            <div>
              <p className="wz-step-hint">{t('security.mfa.verifyHint')}</p>
              <input
                className="admin-input mfa-code-input"
                value={code}
                onChange={(e) => setCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
                placeholder="000000"
                inputMode="numeric"
                autoFocus
              />
            </div>
          )}

          {phase === 'backup' && setup && (
            <div>
              <p className="wz-step-hint">{t('security.mfa.backupHint')}</p>
              <div className="mfa-backup-grid">
                {setup.backup_codes.map((c) => (
                  <span key={c} className="mfa-backup-code">
                    {c}
                  </span>
                ))}
              </div>
              <div className="mfa-backup-actions">
                <button className="admin-btn admin-btn-secondary admin-btn-sm" onClick={copyCodes}>
                  {copied ? <Check size={15} /> : <Copy size={15} />}
                  {t('security.mfa.copyCodes')}
                </button>
                <button
                  className="admin-btn admin-btn-secondary admin-btn-sm"
                  onClick={downloadCodes}
                >
                  <Download size={15} />
                  {t('security.mfa.downloadCodes')}
                </button>
              </div>
              <div className="mfa-warn">
                <AlertTriangle size={16} style={{ flexShrink: 0 }} />
                {t('security.mfa.backupWarn')}
              </div>
            </div>
          )}
        </div>

        <div className="admin-modal-footer">
          {phase === 'status' && (
            <>
              <button className="admin-btn admin-btn-ghost" onClick={onClose} disabled={busy}>
                {t('common.close')}
              </button>
              {enabled ? (
                <button className="admin-btn admin-btn-danger" onClick={disable} disabled={busy}>
                  {busy ? <span className="admin-spinner" /> : t('security.mfa.disable')}
                </button>
              ) : (
                <button
                  className="admin-btn admin-btn-primary"
                  onClick={beginEnroll}
                  disabled={busy}
                >
                  {busy ? <span className="admin-spinner" /> : t('security.mfa.enable')}
                </button>
              )}
            </>
          )}

          {phase === 'scan' && (
            <>
              <button className="admin-btn admin-btn-ghost" onClick={onClose} disabled={busy}>
                {t('common.cancel')}
              </button>
              <button className="admin-btn admin-btn-primary" onClick={() => setPhase('verify')}>
                {t('common.next')}
              </button>
            </>
          )}

          {phase === 'verify' && (
            <>
              <button className="admin-btn admin-btn-ghost" onClick={() => setPhase('scan')}>
                {t('common.back')}
              </button>
              <button
                className="admin-btn admin-btn-primary"
                onClick={verify}
                disabled={busy || code.length !== 6}
              >
                {busy ? <span className="admin-spinner" /> : t('security.mfa.verifyEnable')}
              </button>
            </>
          )}

          {phase === 'backup' && (
            <button
              className="admin-btn admin-btn-primary"
              onClick={onClose}
              style={{ marginLeft: 'auto' }}
            >
              {t('security.mfa.done')}
            </button>
          )}
        </div>
      </div>
    </div>
  );
};

export default MfaSecurityModal;
