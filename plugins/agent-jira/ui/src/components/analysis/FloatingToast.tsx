import { createPortal } from 'react-dom';
import { CheckCircle2, XCircle } from 'lucide-react';

export type ToastPayload = { message: string; tone?: 'success' | 'error' };

const FloatingToast = ({ payload }: { payload: ToastPayload | null }) => {
  if (!payload || typeof document === 'undefined') return null;
  const tone = payload.tone || 'success';
  const Icon = tone === 'error' ? XCircle : CheckCircle2;
  return createPortal(
    <div
      className={`toast ${tone === 'error' ? 'error' : 'success'} toast-floating`}
      role="status"
      aria-live="polite"
    >
      <Icon size={16} />
      <div className="toast-copy">
        <div className="toast-title">Esito operazione</div>
        <div className="toast-message">{payload.message}</div>
      </div>
    </div>,
    document.body
  );
};

export default FloatingToast;
