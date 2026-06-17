/**
 * Confirm Modal
 *
 * Generic confirmation dialog for destructive actions.
 */

import { AlertTriangle, X } from 'lucide-react';
import { useTranslation } from 'react-i18next';

interface ConfirmModalProps {
  title: string;
  message: string;
  confirmLabel?: string;
  isDanger?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
  isLoading?: boolean;
}

const ConfirmModal = ({
  title,
  message,
  confirmLabel,
  isDanger = false,
  onConfirm,
  onCancel,
  isLoading = false,
}: ConfirmModalProps) => {
  const { t } = useTranslation();
  const resolvedConfirmLabel = confirmLabel ?? t('modals.confirm.defaultConfirm');
  return (
    <div className="admin-modal-overlay" onClick={onCancel}>
      <div
        className="admin-modal"
        style={{ maxWidth: '400px' }}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="admin-modal-header">
          <h2 className="admin-modal-title">{title}</h2>
          <button className="admin-btn admin-btn-ghost admin-btn-icon" onClick={onCancel}>
            <X size={18} />
          </button>
        </div>

        <div className="admin-modal-body">
          {isDanger && (
            <div
              style={{
                display: 'flex',
                justifyContent: 'center',
                marginBottom: '1rem',
              }}
            >
              <div
                style={{
                  width: '48px',
                  height: '48px',
                  borderRadius: '50%',
                  background: 'hsla(0, 70%, 50%, 0.15)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                }}
              >
                <AlertTriangle size={24} color="var(--admin-error)" />
              </div>
            </div>
          )}

          <p
            style={{
              textAlign: 'center',
              color: 'var(--admin-text-muted)',
              lineHeight: 1.6,
            }}
          >
            {message}
          </p>
        </div>

        <div className="admin-modal-footer">
          <button className="admin-btn admin-btn-secondary" onClick={onCancel} disabled={isLoading}>
            {t('common.cancel')}
          </button>
          <button
            className={`admin-btn ${isDanger ? 'admin-btn-danger' : 'admin-btn-primary'}`}
            onClick={onConfirm}
            disabled={isLoading}
          >
            {isLoading ? <span className="admin-spinner" /> : resolvedConfirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
};

export default ConfirmModal;
