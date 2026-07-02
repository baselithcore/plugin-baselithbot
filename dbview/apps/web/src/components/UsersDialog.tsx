import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import * as Dialog from '@radix-ui/react-dialog';
import { AnimatePresence, motion } from 'framer-motion';
import {
  CheckCircle2,
  Loader2,
  Pencil,
  Plus,
  ShieldAlert,
  ShieldCheck,
  Trash2,
  UserPlus,
  Users,
  X,
} from 'lucide-react';
import { toast } from 'sonner';
import type { InviteRequest, Role, UpdateUserRequest, UserPublic } from '@dbview/shared';
import { useAppStore } from '../store/app.js';
import { api } from '../lib/api.js';
import { getCurrentUser } from '../lib/auth.js';
import { cn } from '../lib/cn.js';

type Mode = 'list' | 'invite' | { kind: 'edit'; user: UserPublic };

export function UsersDialog() {
  const open = useAppStore((s) => s.usersOpen);
  const setOpen = useAppStore((s) => s.setUsersOpen);
  const [mode, setMode] = useState<Mode>('list');

  return (
    <Dialog.Root
      open={open}
      onOpenChange={(v) => {
        setOpen(v);
        if (!v) setMode('list');
      }}
      modal={false}
    >
      <AnimatePresence>
        {open && (
          <Dialog.Portal forceMount>
            <div
              onClick={() => setOpen(false)}
              className="fixed inset-0 z-40 bg-black/40 backdrop-blur-sm animate-fade-in"
              aria-hidden
            />
            <Dialog.Content className="fixed inset-0 z-50 grid place-items-center pointer-events-none focus:outline-none">
              <motion.div
                initial={{ opacity: 0, y: 8, scale: 0.985 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                exit={{ opacity: 0, y: 6, scale: 0.99 }}
                transition={{ duration: 0.22, ease: [0.22, 1, 0.36, 1] }}
                className="pointer-events-auto w-[680px] max-w-[94vw] rounded-lg border shadow-2xl overflow-hidden"
                style={{
                  background:
                    'linear-gradient(180deg, rgb(var(--surface-elevated)), rgb(var(--surface-1)))',
                  borderColor: 'rgb(var(--border-subtle))',
                }}
              >
                <div
                  className="flex items-center justify-between px-4 h-12 border-b"
                  style={{ borderColor: 'rgb(var(--border-subtle))' }}
                >
                  <Dialog.Title className="flex items-center gap-2 text-[14px] font-semibold">
                    <Users className="w-4 h-4" />
                    {mode === 'list'
                      ? 'Users'
                      : mode === 'invite'
                        ? 'Invite user'
                        : `Edit ${mode.user.email}`}
                  </Dialog.Title>
                  <Dialog.Close className="btn-icon" aria-label="Close">
                    <X className="w-4 h-4" />
                  </Dialog.Close>
                </div>

                <div className="p-4">
                  {mode === 'list' && (
                    <UserList
                      onInvite={() => setMode('invite')}
                      onEdit={(u) => setMode({ kind: 'edit', user: u })}
                    />
                  )}
                  {mode === 'invite' && <InviteForm onDone={() => setMode('list')} />}
                  {typeof mode === 'object' && mode.kind === 'edit' && (
                    <EditForm user={mode.user} onDone={() => setMode('list')} />
                  )}
                </div>
              </motion.div>
            </Dialog.Content>
          </Dialog.Portal>
        )}
      </AnimatePresence>
    </Dialog.Root>
  );
}

function UserList({ onInvite, onEdit }: { onInvite: () => void; onEdit: (u: UserPublic) => void }) {
  const qc = useQueryClient();
  const me = getCurrentUser();
  const { data, isLoading, error } = useQuery({
    queryKey: ['users'],
    queryFn: () => api.listUsers(),
    staleTime: 10_000,
  });

  const del = useMutation({
    mutationFn: (id: string) => api.deleteUser(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['users'] });
      toast.success('User removed');
    },
    onError: (e: Error) => toast.error('Delete failed', { description: e.message }),
  });

  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-center justify-between">
        <p className="text-[12px] text-text-muted">
          Invite-only. Admins can create, edit, and remove accounts.
        </p>
        <button onClick={onInvite} className="btn-primary text-[12px]">
          <UserPlus className="w-3.5 h-3.5" />
          Invite
        </button>
      </div>

      {isLoading && (
        <div className="flex items-center justify-center py-8 text-text-muted">
          <Loader2 className="w-4 h-4 animate-spin" />
        </div>
      )}
      {error && (
        <div className="rounded-md border border-rose-500/40 bg-rose-500/5 px-3 py-2 text-[12px] text-rose-300">
          {(error as Error).message}
        </div>
      )}

      {data && (
        <div
          className="rounded-md border overflow-hidden"
          style={{ borderColor: 'rgb(var(--border-subtle))' }}
        >
          <table className="w-full text-[12px]">
            <thead
              className="text-[10px] uppercase tracking-wide text-text-dim"
              style={{ background: 'rgb(var(--surface-2) / 0.5)' }}
            >
              <tr>
                <th className="text-left px-3 py-2 font-medium">Email</th>
                <th className="text-left px-3 py-2 font-medium">Display name</th>
                <th className="text-left px-3 py-2 font-medium">Role</th>
                <th className="text-left px-3 py-2 font-medium">Status</th>
                <th className="text-right px-3 py-2 font-medium">Actions</th>
              </tr>
            </thead>
            <tbody>
              {data.map((u) => {
                const isSelf = me?.id === u.id;
                return (
                  <tr
                    key={u.id}
                    className="border-t"
                    style={{ borderColor: 'rgb(var(--border-subtle))' }}
                  >
                    <td className="px-3 py-2 font-mono text-[11px]">{u.email}</td>
                    <td className="px-3 py-2 text-text-muted">{u.displayName ?? '—'}</td>
                    <td className="px-3 py-2">
                      <span className="inline-flex items-center gap-1">
                        {u.role === 'admin' ? (
                          <ShieldCheck className="w-3 h-3 text-accent" />
                        ) : (
                          <ShieldAlert className="w-3 h-3 text-text-dim" />
                        )}
                        {u.role}
                      </span>
                    </td>
                    <td className="px-3 py-2">
                      <span
                        className={cn(
                          'inline-flex items-center gap-1 text-[11px]',
                          u.isActive ? 'text-emerald-400' : 'text-text-dim',
                        )}
                      >
                        {u.isActive ? <CheckCircle2 className="w-3 h-3" /> : null}
                        {u.isActive ? 'Active' : 'Disabled'}
                      </span>
                    </td>
                    <td className="px-3 py-2 text-right">
                      <div className="inline-flex items-center gap-1">
                        <button
                          onClick={() => onEdit(u)}
                          className="btn-icon w-7 h-7"
                          aria-label={`Edit ${u.email}`}
                          title="Edit"
                        >
                          <Pencil className="w-3.5 h-3.5" />
                        </button>
                        <button
                          onClick={() => {
                            if (isSelf) {
                              toast.error('Cannot delete your own account');
                              return;
                            }
                            if (!confirm(`Delete ${u.email}?`)) return;
                            del.mutate(u.id);
                          }}
                          className="btn-icon w-7 h-7"
                          aria-label={`Delete ${u.email}`}
                          title={isSelf ? 'Cannot delete self' : 'Delete'}
                          disabled={isSelf || del.isPending}
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })}
              {data.length === 0 && (
                <tr>
                  <td colSpan={5} className="px-3 py-6 text-center text-text-muted">
                    No users yet.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

function InviteForm({ onDone }: { onDone: () => void }) {
  const qc = useQueryClient();
  const [form, setForm] = useState<InviteRequest>({
    email: '',
    displayName: '',
    role: 'user',
    password: '',
  });

  const m = useMutation({
    mutationFn: (body: InviteRequest) => api.inviteUser(body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['users'] });
      toast.success('User invited');
      onDone();
    },
    onError: (e: Error) => toast.error('Invite failed', { description: e.message }),
  });

  return (
    <form
      className="flex flex-col gap-3"
      onSubmit={(e) => {
        e.preventDefault();
        const body: InviteRequest = {
          email: form.email.trim(),
          role: form.role,
          password: form.password,
          ...(form.displayName?.trim() ? { displayName: form.displayName.trim() } : {}),
        };
        m.mutate(body);
      }}
    >
      <Field label="Email">
        <input
          type="email"
          required
          autoFocus
          autoComplete="off"
          className="input"
          value={form.email}
          onChange={(e) => setForm({ ...form, email: e.target.value })}
        />
      </Field>
      <Field label="Display name (optional)">
        <input
          type="text"
          maxLength={120}
          className="input"
          value={form.displayName ?? ''}
          onChange={(e) => setForm({ ...form, displayName: e.target.value })}
        />
      </Field>
      <Field label="Role">
        <RoleSelect value={form.role} onChange={(role) => setForm({ ...form, role })} />
      </Field>
      <Field label="Initial password (≥12 chars)">
        <input
          type="password"
          required
          minLength={12}
          maxLength={200}
          autoComplete="new-password"
          className="input font-mono"
          value={form.password}
          onChange={(e) => setForm({ ...form, password: e.target.value })}
        />
      </Field>
      <div className="flex items-center justify-end gap-2 pt-1">
        <button type="button" onClick={onDone} className="btn">
          Cancel
        </button>
        <button type="submit" className="btn-primary" disabled={m.isPending}>
          {m.isPending ? (
            <Loader2 className="w-3.5 h-3.5 animate-spin" />
          ) : (
            <Plus className="w-3.5 h-3.5" />
          )}
          Create
        </button>
      </div>
    </form>
  );
}

function EditForm({ user, onDone }: { user: UserPublic; onDone: () => void }) {
  const qc = useQueryClient();
  const me = getCurrentUser();
  const isSelf = me?.id === user.id;
  const [displayName, setDisplayName] = useState(user.displayName ?? '');
  const [role, setRole] = useState<Role>(user.role);
  const [isActive, setIsActive] = useState(user.isActive);
  const [password, setPassword] = useState('');

  const m = useMutation({
    mutationFn: (body: UpdateUserRequest) => api.updateUser(user.id, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['users'] });
      toast.success('User updated');
      onDone();
    },
    onError: (e: Error) => toast.error('Update failed', { description: e.message }),
  });

  return (
    <form
      className="flex flex-col gap-3"
      onSubmit={(e) => {
        e.preventDefault();
        const body: UpdateUserRequest = {};
        const trimmedName = displayName.trim();
        if (trimmedName && trimmedName !== (user.displayName ?? '')) body.displayName = trimmedName;
        if (role !== user.role) body.role = role;
        if (isActive !== user.isActive) body.isActive = isActive;
        if (password) body.password = password;
        if (Object.keys(body).length === 0) {
          toast.message('No changes');
          return;
        }
        m.mutate(body);
      }}
    >
      <Field label="Email">
        <input className="input font-mono opacity-60" value={user.email} readOnly disabled />
      </Field>
      <Field label="Display name">
        <input
          type="text"
          maxLength={120}
          className="input"
          value={displayName}
          onChange={(e) => setDisplayName(e.target.value)}
        />
      </Field>
      <Field label="Role">
        <RoleSelect value={role} onChange={setRole} disabled={isSelf} />
        {isSelf && <p className="text-[11px] text-text-dim mt-1">Cannot change your own role.</p>}
      </Field>
      <Field label="Status">
        <label className="inline-flex items-center gap-2 text-[12px]">
          <input
            type="checkbox"
            checked={isActive}
            onChange={(e) => setIsActive(e.target.checked)}
            disabled={isSelf}
          />
          Active
        </label>
        {isSelf && (
          <p className="text-[11px] text-text-dim mt-1">Cannot disable your own account.</p>
        )}
      </Field>
      <Field label="Reset password (optional, ≥12 chars)">
        <input
          type="password"
          minLength={12}
          maxLength={200}
          autoComplete="new-password"
          className="input font-mono"
          placeholder="leave blank to keep current"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />
      </Field>
      <div className="flex items-center justify-end gap-2 pt-1">
        <button type="button" onClick={onDone} className="btn">
          Cancel
        </button>
        <button type="submit" className="btn-primary" disabled={m.isPending}>
          {m.isPending ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : null}
          Save
        </button>
      </div>
    </form>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="flex flex-col gap-1">
      <span className="text-[11px] uppercase tracking-wider text-text-dim">{label}</span>
      {children}
    </label>
  );
}

function RoleSelect({
  value,
  onChange,
  disabled,
}: {
  value: Role;
  onChange: (r: Role) => void;
  disabled?: boolean;
}) {
  return (
    <select
      className="input"
      value={value}
      onChange={(e) => onChange(e.target.value as Role)}
      disabled={disabled}
    >
      <option value="user">user</option>
      <option value="admin">admin</option>
    </select>
  );
}
