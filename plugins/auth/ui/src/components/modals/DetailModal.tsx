import React from 'react';
import { X, Copy, Check } from 'lucide-react';
import { useTranslation } from 'react-i18next';

interface DetailModalProps {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  data: Record<string, unknown> | null;
  formatters?: Record<string, (value: any) => React.ReactNode>;
}

const DetailModal: React.FC<DetailModalProps> = ({ isOpen, onClose, title, data, formatters }) => {
  const { t } = useTranslation();
  const [copied, setCopied] = React.useState(false);

  if (!isOpen || !data) return null;

  const handleCopy = () => {
    navigator.clipboard.writeText(JSON.stringify(data, null, 2));
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const renderValue = (key: string, value: any) => {
    if (formatters && formatters[key]) {
      return formatters[key](value);
    }

    if (value === null || value === undefined) {
      return <span className="text-muted">{t('common.nullValue')}</span>;
    }

    if (typeof value === 'boolean') {
      return (
        <span className={value ? 'text-success' : 'text-danger'}>
          {value ? t('common.true') : t('common.false')}
        </span>
      );
    }

    if (typeof value === 'object') {
      return <pre className="detail-json">{JSON.stringify(value, null, 2)}</pre>;
    }

    return String(value);
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-container detail-modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h3>{title}</h3>
          <div className="modal-actions">
            <button
              className="admin-btn admin-btn-ghost admin-btn-icon"
              onClick={handleCopy}
              title={t('modals.detail.copyJson')}
            >
              {copied ? <Check size={16} className="text-success" /> : <Copy size={16} />}
            </button>
            <button
              className="admin-btn admin-btn-ghost admin-btn-icon"
              onClick={onClose}
              title={t('common.close')}
            >
              <X size={20} />
            </button>
          </div>
        </div>

        <div className="modal-content">
          <div className="detail-grid">
            {Object.entries(data).map(([key, value]) => (
              <div key={key} className="detail-item">
                <div className="detail-label">{key.replace(/_/g, ' ')}</div>
                <div className="detail-value">{renderValue(key, value)}</div>
              </div>
            ))}
          </div>
        </div>

        <style>{`
          .detail-modal {
            max-width: 600px;
            width: 90%;
            max-height: 85vh;
            display: flex;
            flex-direction: column;
          }

          .modal-actions {
            display: flex;
            align-items: center;
            gap: 0.5rem;
          }

          .detail-grid {
            display: grid;
            gap: 1rem;
          }

          .detail-item {
            display: flex;
            flex-direction: column;
            gap: 0.375rem;
            padding-bottom: 1rem;
            border-bottom: 1px solid var(--admin-table-border);
          }

          .detail-item:last-child {
            border-bottom: none;
            padding-bottom: 0;
          }

          .detail-label {
            font-size: 0.75rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            color: var(--admin-text-muted);
            font-weight: 600;
          }

          .detail-value {
            font-size: 0.875rem;
            color: var(--admin-text);
            word-break: break-all;
            line-height: 1.6;
          }

          .detail-json {
            margin: 0;
            padding: 0.75rem;
            background: hsla(220, 25%, 10%, 0.5);
            border: 1px solid var(--admin-table-border);
            border-radius: var(--admin-radius-sm);
            font-family: 'SF Mono', 'Fira Code', 'Consolas', monospace;
            font-size: 0.8125rem;
            color: var(--admin-text-muted);
            overflow-x: auto;
          }

          .text-muted { color: var(--admin-text-muted); }
          .text-success { color: var(--admin-success); }
          .text-danger { color: var(--admin-error); }
          
          /* Reuse existing modal styles from AdminPanel.css or insert here if needed */
          .modal-overlay {
            position: fixed;
            inset: 0;
            background: rgba(0, 0, 0, 0.7);
            backdrop-filter: blur(4px);
            display: flex;
            align-items: center;
            justify-content: center;
            z-index: 1000;
            animation: fadeIn 0.15s ease;
          }

          .modal-container {
            background: var(--admin-card-bg-solid);
            border: 1px solid var(--admin-card-border);
            border-radius: var(--admin-radius-xl);
            box-shadow: var(--admin-card-shadow);
            animation: slideUp 0.2s ease;
            overflow: hidden;
            display: flex;
            flex-direction: column;
          }

          .modal-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 1.25rem 1.5rem;
            border-bottom: 1px solid var(--admin-table-border);
            background: var(--admin-table-header-bg);
          }

          .modal-header h3 {
            margin: 0;
            font-size: 1.125rem;
            font-weight: 600;
            color: var(--admin-text);
            letter-spacing: -0.02em;
          }

          .modal-content {
            padding: 1.5rem;
            overflow-y: auto;
          }

          @keyframes fadeIn {
            from { opacity: 0; }
            to { opacity: 1; }
          }

          @keyframes slideUp {
            from { opacity: 0; transform: translateY(10px); }
            to { opacity: 1; transform: translateY(0); }
          }
        `}</style>
      </div>
    </div>
  );
};

export default DetailModal;
