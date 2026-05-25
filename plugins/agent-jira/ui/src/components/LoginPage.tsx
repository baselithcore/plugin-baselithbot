import { useState } from 'react';
import {
  LogIn,
  UserPlus,
  Mail,
  Lock,
  User,
  Building2,
  Loader2,
  AlertCircle,
  CheckCircle2,
  Zap,
} from 'lucide-react';

type Props = {
  onLogin: (email: string, password: string) => Promise<any>;
  onRegister: (
    email: string,
    password: string,
    displayName?: string,
    organization?: string
  ) => Promise<any>;
  error: string | null;
  loading: boolean;
};

const LoginPage = ({ onLogin, onRegister, error, loading }: Props) => {
  const [mode, setMode] = useState<'login' | 'register'>('login');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [displayName, setDisplayName] = useState('');
  const [organization, setOrganization] = useState('');
  const [localError, setLocalError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLocalError(null);
    setSuccessMessage(null);

    if (!email.includes('@')) {
      setLocalError('Inserisci un indirizzo email valido.');
      return;
    }
    if (password.length < 8) {
      setLocalError('La password deve contenere almeno 8 caratteri.');
      return;
    }

    try {
      if (mode === 'login') {
        await onLogin(email, password);
      } else {
        await onRegister(email, password, displayName, organization);
        // Registration succeeded — show success and switch to login
        setSuccessMessage('Account creato con successo! Accedi con le tue credenziali.');
        setPassword('');
        setDisplayName('');
        setOrganization('');
        setMode('login');
      }
    } catch {
      // Error is handled by the hook
    }
  };

  const displayError = localError || error;

  return (
    <div className="auth-page">
      <div className="auth-glow auth-glow-1" />
      <div className="auth-glow auth-glow-2" />

      <div className="auth-card">
        {/* Logo */}
        <div className="auth-logo">
          <Zap size={28} />
          <span>agent-jira</span>
        </div>

        <p className="auth-subtitle">
          {mode === 'login' ? 'Accedi al tuo workspace' : 'Crea il tuo account e workspace'}
        </p>

        {/* Mode toggle */}
        <div className="auth-toggle">
          <button
            className={`auth-toggle-btn ${mode === 'login' ? 'auth-toggle-btn--active' : ''}`}
            onClick={() => {
              setMode('login');
              setLocalError(null);
            }}
          >
            <LogIn size={14} />
            Accedi
          </button>
          <button
            className={`auth-toggle-btn ${mode === 'register' ? 'auth-toggle-btn--active' : ''}`}
            onClick={() => {
              setMode('register');
              setLocalError(null);
              setSuccessMessage(null);
            }}
          >
            <UserPlus size={14} />
            Registrati
          </button>
        </div>

        {/* Success message */}
        {successMessage && (
          <div className="auth-success">
            <CheckCircle2 size={14} />
            <span>{successMessage}</span>
          </div>
        )}

        {/* Form */}
        <form className="auth-form" onSubmit={handleSubmit}>
          {mode === 'register' && (
            <>
              <div className="auth-field">
                <label className="auth-field-label">
                  <User size={13} /> Nome
                </label>
                <input
                  className="auth-input"
                  type="text"
                  placeholder="Il tuo nome"
                  value={displayName}
                  onChange={(e) => setDisplayName(e.target.value)}
                />
              </div>
              <div className="auth-field">
                <label className="auth-field-label">
                  <Building2 size={13} /> Organizzazione
                </label>
                <input
                  className="auth-input"
                  type="text"
                  placeholder="Nome azienda o team"
                  value={organization}
                  onChange={(e) => setOrganization(e.target.value)}
                />
                <span className="auth-field-hint">Verrà creato un workspace dedicato</span>
              </div>
            </>
          )}

          <div className="auth-field">
            <label className="auth-field-label">
              <Mail size={13} /> Email
            </label>
            <input
              className="auth-input"
              type="email"
              placeholder="nome@azienda.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              autoFocus
              required
            />
          </div>

          <div className="auth-field">
            <label className="auth-field-label">
              <Lock size={13} /> Password
            </label>
            <input
              className="auth-input"
              type="password"
              placeholder={mode === 'register' ? 'Min. 8 caratteri' : 'La tua password'}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              minLength={8}
            />
          </div>

          {displayError && (
            <div className="auth-error">
              <AlertCircle size={14} />
              <span>{displayError}</span>
            </div>
          )}

          <button className="auth-submit" type="submit" disabled={loading}>
            {loading ? (
              <Loader2 size={16} className="ws-spin" />
            ) : mode === 'login' ? (
              <LogIn size={16} />
            ) : (
              <UserPlus size={16} />
            )}
            {loading ? 'Caricamento...' : mode === 'login' ? 'Accedi' : 'Crea account'}
          </button>
        </form>

        <p className="auth-footer-text">
          {mode === 'login' ? (
            <>
              Non hai un account?{' '}
              <button
                className="auth-link"
                onClick={() => {
                  setMode('register');
                  setLocalError(null);
                  setSuccessMessage(null);
                }}
              >
                Registrati
              </button>
            </>
          ) : (
            <>
              Hai già un account?{' '}
              <button
                className="auth-link"
                onClick={() => {
                  setMode('login');
                  setLocalError(null);
                }}
              >
                Accedi
              </button>
            </>
          )}
        </p>
      </div>
    </div>
  );
};

export default LoginPage;
