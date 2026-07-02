import { useState, type FormEvent } from 'react';
import { Lock, ShieldAlert } from 'lucide-react';
import { api } from '../lib/api.js';
import { logoutRequest, setSession } from '../lib/auth.js';

interface Props {
  email: string;
  onChanged: () => void;
}

export function ChangePasswordPage({ email, onChanged }: Props) {
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirm, setConfirm] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const mismatch = confirm.length > 0 && confirm !== newPassword;
  const sameAsOld = newPassword.length > 0 && newPassword === currentPassword;
  const canSubmit =
    !submitting &&
    currentPassword.length > 0 &&
    newPassword.length >= 12 &&
    !mismatch &&
    !sameAsOld;

  async function handleSubmit(e: FormEvent): Promise<void> {
    e.preventDefault();
    if (!canSubmit) return;
    setError(null);
    setSubmitting(true);
    try {
      const res = await api.changePassword({ currentPassword, newPassword });
      setSession(res.accessToken, res.user);
      onChanged();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Change failed.');
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="h-screen w-screen flex items-center justify-center bg-surface-0 text-text">
      <form
        onSubmit={handleSubmit}
        className="panel w-full max-w-sm p-6 flex flex-col gap-4"
        aria-label="Change password"
      >
        <header className="flex flex-col items-center gap-2 pb-2">
          <ShieldAlert className="w-7 h-7 text-amber-400" aria-hidden />
          <h1 className="text-base font-semibold tracking-tight">Set a new password</h1>
          <p className="text-xs text-text-muted text-center">
            Your account requires a password change before you can continue.
          </p>
          <p className="text-[11px] font-mono text-text-dim">{email}</p>
        </header>

        <PasswordField
          label="Current password"
          autoComplete="current-password"
          value={currentPassword}
          onChange={setCurrentPassword}
        />

        <PasswordField
          label="New password (min 12 chars)"
          autoComplete="new-password"
          minLength={12}
          value={newPassword}
          onChange={setNewPassword}
        />

        <PasswordField
          label="Confirm new password"
          autoComplete="new-password"
          minLength={12}
          value={confirm}
          onChange={setConfirm}
        />

        {sameAsOld && (
          <p className="text-[11px] text-amber-300">New password must differ from current one.</p>
        )}
        {mismatch && <p className="text-[11px] text-rose-300">Passwords do not match.</p>}
        {error && (
          <div
            role="alert"
            className="text-xs text-rose-300 bg-rose-500/10 border border-rose-500/30 rounded px-3 py-2"
          >
            {error}
          </div>
        )}

        <button
          type="submit"
          disabled={!canSubmit}
          className="btn btn-primary w-full justify-center"
        >
          {submitting ? 'Updating…' : 'Update password'}
        </button>

        <button
          type="button"
          onClick={() => void logoutRequest()}
          className="text-[11px] text-text-dim hover:text-text underline self-center"
        >
          Sign out instead
        </button>
      </form>
    </div>
  );
}

function PasswordField({
  label,
  value,
  onChange,
  autoComplete,
  minLength,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  autoComplete: string;
  minLength?: number;
}) {
  return (
    <label className="flex flex-col gap-1 text-xs">
      <span className="text-text-muted">{label}</span>
      <div className="relative">
        <Lock
          className="absolute left-2 top-1/2 -translate-y-1/2 w-4 h-4 text-text-dim"
          aria-hidden
        />
        <input
          type="password"
          required
          autoComplete={autoComplete}
          minLength={minLength}
          maxLength={200}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          className="input pl-8 w-full font-mono"
          placeholder="••••••••••••"
        />
      </div>
    </label>
  );
}
