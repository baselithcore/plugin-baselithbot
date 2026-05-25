import { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { api, type TargetRecord } from '../../lib/api';
import { Button, Card, ConfirmDialog, Icon } from '../../components/ui';
import { KIND_META } from '../../lib/targets';
import { relTime } from './_utils';
import { ScannersCard } from './ScannersCard';

export function SettingsTab({
  target,
  onArchive,
}: {
  target: TargetRecord;
  onArchive: () => void;
}) {
  const nav = useNavigate();
  const qc = useQueryClient();
  const [confirmDelete, setConfirmDelete] = useState(false);
  const archived = target.archived_at !== null;

  const remove = useMutation({
    mutationFn: () => api.deleteTarget(target.id, { hard: true, purgeRuns: true }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['targets'] });
      nav('/targets');
    },
  });

  return (
    <div className="space-y-4">
      <Card title="Target metadata">
        <dl className="grid gap-4 sm:grid-cols-2">
          <Row label="Kind" value={KIND_META[target.kind].label} />
          <Row label="Value" value={target.value} mono />
          <Row label="Environment" value={target.environment ?? '—'} />
          <Row label="Owner" value={target.owner ?? '—'} />
          <Row label="Schedule" value={target.schedule_cron ?? 'on-demand'} mono />
          <Row label="Created" value={relTime(target.created_at)} />
        </dl>
      </Card>
      <ScannersCard target={target} />
      <Card title="Danger zone" className="border-sev-critical/30">
        <div className="space-y-4">
          <div className="flex items-start justify-between gap-4">
            <div>
              <h4 className="font-display text-sm font-medium text-text-primary">
                {archived ? 'Target archived' : 'Archive target'}
              </h4>
              <p className="mt-1 text-xs text-text-muted">
                Hides this target from the active list and disables its schedule. History is
                preserved and the target can be restored from filters.
              </p>
            </div>
            <Button variant="secondary" onClick={onArchive} disabled={archived}>
              <Icon.Archive size={14} />
              {archived ? 'Archived' : 'Archive'}
            </Button>
          </div>
          <div className="border-t border-bg-line/60" />
          <div className="flex items-start justify-between gap-4">
            <div>
              <h4 className="font-display text-sm font-medium text-sev-critical">
                Delete permanently
              </h4>
              <p className="mt-1 text-xs text-text-muted">
                Removes this target along with every scan run and finding attached to it. This
                cannot be undone.
              </p>
            </div>
            <Button variant="danger" onClick={() => setConfirmDelete(true)}>
              <Icon.Trash size={14} />
              Delete
            </Button>
          </div>
        </div>
      </Card>

      <ConfirmDialog
        open={confirmDelete}
        onClose={() => setConfirmDelete(false)}
        onConfirm={() => remove.mutateAsync()}
        title="Delete target permanently?"
        description={
          <>
            You are about to delete{' '}
            <span className="font-mono text-text-primary">{target.name}</span> and everything
            attached to it.
          </>
        }
        consequences={[
          'All scan runs against this target will be deleted.',
          'All findings discovered on this target will be deleted.',
          'Audit log entries are preserved for compliance.',
          'This action cannot be undone.',
        ]}
        confirmText={target.name}
        confirmLabel="Delete forever"
        tone="danger"
        busy={remove.isPending}
      />
    </div>
  );
}

function Row({ label, value, mono }: { label: string; value: React.ReactNode; mono?: boolean }) {
  return (
    <div>
      <dt className="text-2xs font-mono uppercase tracking-wider text-text-muted">{label}</dt>
      <dd className={`mt-1 text-sm text-text-primary ${mono ? 'font-mono' : ''}`}>{value}</dd>
    </div>
  );
}
