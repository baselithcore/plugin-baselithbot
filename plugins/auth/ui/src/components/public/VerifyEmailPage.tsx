/** Email-verification landing page: consumes token from the URL on mount. */

import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { verifyEmail } from '../../api/recovery';
import AuthShell from './AuthShell';

type State = 'pending' | 'ok' | 'error';

export default function VerifyEmailPage() {
  const { t } = useTranslation();
  const [state, setState] = useState<State>('pending');
  const [message, setMessage] = useState('');

  useEffect(() => {
    const token = new URLSearchParams(window.location.search).get('token') || '';
    if (!token) {
      setState('error');
      setMessage(t('recovery.invalidLink'));
      return;
    }
    verifyEmail(token)
      .then((r) => {
        setState('ok');
        setMessage(r.message);
      })
      .catch((err) => {
        setState('error');
        setMessage(err instanceof Error ? err.message : t('recovery.genericError'));
      });
  }, [t]);

  return (
    <AuthShell title={t('recovery.verifyTitle')}>
      <div className="auth-form">
        {state === 'pending' && (
          <div className="auth-center">
            <span className="auth-spinner" />
          </div>
        )}
        {state === 'ok' && <div className="auth-success">{message}</div>}
        {state === 'error' && <div className="auth-error">{message}</div>}
        <a className="auth-button" href="/auth/login">
          {t('recovery.backToLogin')}
        </a>
      </div>
    </AuthShell>
  );
}
