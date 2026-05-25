/**
 * Reset Password Modal
 *
 * Displays the temporary password after reset or user creation.
 */

import { useState } from 'react';
import { X, Copy, Check, AlertTriangle } from 'lucide-react';
import type { ResetPasswordResponse } from '../../types';

interface ResetPasswordModalProps {
  result: ResetPasswordResponse;
  onClose: () => void;
}

const ResetPasswordModal = ({ result, onClose }: ResetPasswordModalProps) => {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    if (!result.temporary_password) return;

    try {
      await navigator.clipboard.writeText(result.temporary_password);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Failed to copy:', err);
    }
  };

  return (
    <div className="admin-modal-overlay" onClick={onClose}>
      <div className="admin-modal" onClick={(e) => e.stopPropagation()}>
        <div className="admin-modal-header">
          <h2 className="admin-modal-title">Password Reset</h2>
          <button className="admin-btn admin-btn-ghost admin-btn-icon" onClick={onClose}>
            <X size={18} />
          </button>
        </div>

        <div className="admin-modal-body">
          <div className="admin-alert admin-alert-success" style={{ marginBottom: '1rem' }}>
            <Check size={18} />
            <span>{result.message}</span>
          </div>

          {result.temporary_password && (
            <>
              <div className="admin-alert admin-alert-warning" style={{ marginBottom: '1rem' }}>
                <AlertTriangle size={18} />
                <span>
                  This password will only be shown once. Please copy it now and share it securely
                  with the user.
                </span>
              </div>

              <div className="admin-password-display">
                <div className="admin-password-display-label">Temporary Password</div>
                <div
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '0.75rem',
                  }}
                >
                  <code className="admin-password-display-value">{result.temporary_password}</code>
                  <button
                    className="admin-btn admin-btn-secondary admin-btn-sm"
                    onClick={handleCopy}
                  >
                    {copied ? <Check size={14} /> : <Copy size={14} />}
                    {copied ? 'Copied!' : 'Copy'}
                  </button>
                </div>
              </div>
            </>
          )}
        </div>

        <div className="admin-modal-footer">
          <button className="admin-btn admin-btn-primary" onClick={onClose}>
            Close
          </button>
        </div>
      </div>
    </div>
  );
};

export default ResetPasswordModal;
