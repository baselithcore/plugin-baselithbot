import { useEffect, useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import * as Dialog from '@radix-ui/react-dialog';
import { AnimatePresence, motion } from 'framer-motion';
import {
  Globe,
  Loader2,
  Lock,
  Save,
  Share2,
  ShieldCheck,
  Users as UsersIcon,
  X,
} from 'lucide-react';
import { toast } from 'sonner';
import type { ConnectionSharing, ConnectionSummary, UserPublic } from '@dbview/shared';
import { api } from '../lib/api.js';
import { cn } from '../lib/cn.js';

type Mode = ConnectionSharing['mode'];

interface Props {
  connection: ConnectionSummary | null;
  onClose: () => void;
}

/**
 * Admin-only dialog for editing a connection's `sharing` policy:
 *   - private: only the owner sees it (other admins are NOT included)
 *   - admins:  every admin sees it; non-admin users do not
 *   - all:     every authenticated user sees it
 *   - users:   listed userIds plus the owner see it
 *
 * Wired to `PATCH /api/connections/:id/sharing` via `api.updateConnectionSharing`.
 */
export function ConnectionSharingDialog({ connection, onClose }: Props) {
  const qc = useQueryClient();
  const [mode, setMode] = useState<Mode>('private');
  const [selected, setSelected] = useState<Set<string>>(new Set());

  useEffect(() => {
    if (!connection) return;
    setMode(connection.sharing.mode);
    setSelected(new Set(connection.sharing.userIds));
  }, [connection]);

  const users = useQuery({
    queryKey: ['users'],
    queryFn: () => api.listUsers(),
    enabled: !!connection,
    staleTime: 10_000,
  });

  const eligible = useMemo<UserPublic[]>(() => {
    if (!users.data) return [];
    // Any active user can be granted explicit access — including other admins.
    // Owners are excluded since they always have access by ownership.
    const ownerId = connection?.ownerId;
    return users.data
      .filter((u) => u.isActive && u.id !== ownerId)
      .sort((a, b) => {
        if (a.role !== b.role) return a.role === 'admin' ? -1 : 1;
        return a.email.localeCompare(b.email);
      });
  }, [users.data, connection?.ownerId]);

  const save = useMutation({
    mutationFn: () => {
      if (!connection) throw new Error('no connection');
      const sharing: ConnectionSharing =
        mode === 'users' ? { mode, userIds: [...selected] } : { mode, userIds: [] };
      return api.updateConnectionSharing(connection.id, sharing);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['connections'] });
      toast.success('Sharing updated');
      onClose();
    },
    onError: (e: Error) => toast.error('Update failed', { description: e.message }),
  });

  const canSave = !(mode === 'users' && selected.size === 0);

  return (
    <Dialog.Root open={!!connection} onOpenChange={(v) => !v && onClose()} modal={false}>
      <AnimatePresence>
        {connection && (
          <Dialog.Portal forceMount>
            <div
              onClick={onClose}
              className="fixed inset-0 z-40 bg-black/40 backdrop-blur-sm animate-fade-in"
              aria-hidden
            />
            <Dialog.Content className="fixed inset-0 z-50 grid place-items-center pointer-events-none focus:outline-none">
              <motion.div
                initial={{ opacity: 0, y: 8, scale: 0.985 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                exit={{ opacity: 0, y: 6, scale: 0.99 }}
                transition={{ duration: 0.22, ease: [0.22, 1, 0.36, 1] }}
                className="pointer-events-auto w-[560px] max-w-[94vw] rounded-lg border shadow-2xl overflow-hidden"
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
                    <Share2 className="w-4 h-4" />
                    Share &quot;{connection.name}&quot;
                  </Dialog.Title>
                  <button className="btn-icon" onClick={onClose} aria-label="Close">
                    <X className="w-4 h-4" />
                  </button>
                </div>

                <div className="p-4 flex flex-col gap-3">
                  <p className="text-[12px] text-text-muted">
                    Choose who can see this connection. Mutations stay restricted to admins.
                  </p>

                  <div className="grid grid-cols-2 gap-2">
                    <ModeCard
                      mode="private"
                      label="Private"
                      desc="Only the owner"
                      icon={<Lock className="w-3.5 h-3.5" />}
                      active={mode === 'private'}
                      onClick={() => setMode('private')}
                    />
                    <ModeCard
                      mode="admins"
                      label="Admins"
                      desc="All admins"
                      icon={<ShieldCheck className="w-3.5 h-3.5" />}
                      active={mode === 'admins'}
                      onClick={() => setMode('admins')}
                    />
                    <ModeCard
                      mode="all"
                      label="Everyone"
                      desc="All active users"
                      icon={<Globe className="w-3.5 h-3.5" />}
                      active={mode === 'all'}
                      onClick={() => setMode('all')}
                    />
                    <ModeCard
                      mode="users"
                      label="Selected"
                      desc="Pick users"
                      icon={<UsersIcon className="w-3.5 h-3.5" />}
                      active={mode === 'users'}
                      onClick={() => setMode('users')}
                    />
                  </div>

                  {mode === 'users' && (
                    <div className="flex flex-col gap-1.5">
                      <div className="flex items-center justify-between">
                        <span className="text-[11px] uppercase tracking-wider text-text-dim">
                          Users
                        </span>
                        <span className="text-[11px] text-text-muted">
                          {selected.size} / {eligible.length}
                        </span>
                      </div>
                      {users.isLoading && (
                        <div className="flex items-center justify-center py-6 text-text-muted">
                          <Loader2 className="w-4 h-4 animate-spin" />
                        </div>
                      )}
                      {users.error && (
                        <div className="rounded-md border border-rose-500/40 bg-rose-500/5 px-3 py-2 text-[12px] text-rose-300">
                          {(users.error as Error).message}
                        </div>
                      )}
                      {eligible.length === 0 && !users.isLoading && (
                        <div className="rounded-md border border-amber-500/40 bg-amber-500/5 px-3 py-2 text-[12px] text-amber-200">
                          No other active users exist yet. Invite users first.
                        </div>
                      )}
                      <div
                        className="rounded-md border max-h-64 overflow-auto"
                        style={{ borderColor: 'rgb(var(--border-subtle))' }}
                      >
                        {eligible.map((u) => {
                          const checked = selected.has(u.id);
                          return (
                            <label
                              key={u.id}
                              className={cn(
                                'flex items-center gap-2 px-3 py-2 cursor-pointer border-b last:border-b-0 text-[12px]',
                                checked && 'bg-accent/5',
                              )}
                              style={{ borderColor: 'rgb(var(--border-subtle))' }}
                            >
                              <input
                                type="checkbox"
                                checked={checked}
                                onChange={(e) => {
                                  const next = new Set(selected);
                                  if (e.target.checked) next.add(u.id);
                                  else next.delete(u.id);
                                  setSelected(next);
                                }}
                              />
                              <span className="font-mono text-[11px]">{u.email}</span>
                              {u.displayName && (
                                <span className="text-text-muted truncate">— {u.displayName}</span>
                              )}
                              {u.role === 'admin' && (
                                <span
                                  className="ml-auto inline-flex items-center gap-0.5 chip text-[9px] px-1 h-4 shrink-0"
                                  title="Administrator"
                                >
                                  <ShieldCheck className="w-2.5 h-2.5" />
                                  admin
                                </span>
                              )}
                            </label>
                          );
                        })}
                      </div>
                    </div>
                  )}

                  <div className="flex items-center justify-end gap-2 pt-2">
                    <button type="button" onClick={onClose} className="btn">
                      Cancel
                    </button>
                    <button
                      type="button"
                      onClick={() => save.mutate()}
                      className="btn-primary"
                      disabled={!canSave || save.isPending}
                      title={canSave ? 'Save sharing' : 'Pick at least one user'}
                    >
                      {save.isPending ? (
                        <Loader2 className="w-3.5 h-3.5 animate-spin" />
                      ) : (
                        <Save className="w-3.5 h-3.5" />
                      )}
                      Save
                    </button>
                  </div>
                </div>
              </motion.div>
            </Dialog.Content>
          </Dialog.Portal>
        )}
      </AnimatePresence>
    </Dialog.Root>
  );
}

function ModeCard({
  label,
  desc,
  icon,
  active,
  onClick,
}: {
  mode: Mode;
  label: string;
  desc: string;
  icon: React.ReactNode;
  active: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        'flex flex-col items-start gap-1 rounded-md border px-3 py-2 text-left transition-all',
        active ? 'ring-1 ring-accent/40 border-accent/40 bg-accent/5' : 'hover:bg-surface-2/60',
      )}
      style={{ borderColor: active ? undefined : 'rgb(var(--border-subtle))' }}
    >
      <div className="flex items-center gap-1.5 text-[12px] font-medium">
        {icon}
        {label}
      </div>
      <span className="text-[10px] text-text-muted">{desc}</span>
    </button>
  );
}
