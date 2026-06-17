import type { WorkspaceSkillSpec } from '../../../../../lib/api';
import { Icon, paths } from '../../../../../lib/icons';

interface FormActionsProps {
  canSubmit: boolean;
  pending: boolean;
  overwrite: boolean;
  setOverwrite: (v: boolean) => void;
  lastCreated: WorkspaceSkillSpec | null;
  onSubmit: () => void;
  onCancel: () => void;
  onReset: () => void;
}

export function FormActions({
  canSubmit,
  pending,
  overwrite,
  setOverwrite,
  lastCreated,
  onSubmit,
  onCancel,
  onReset,
}: FormActionsProps) {
  return (
    <>
      <label style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
        <input
          type="checkbox"
          checked={overwrite}
          onChange={(event) => setOverwrite(event.target.checked)}
        />
        <span>Overwrite existing bundle with the same slug</span>
      </label>

      <div className="inline" style={{ gap: 8 }}>
        <button type="button" className="btn primary" disabled={!canSubmit} onClick={onSubmit}>
          <Icon path={paths.plus} size={12} />
          {pending ? 'Creating…' : 'Create skill'}
        </button>
        <button type="button" className="btn ghost sm" onClick={onCancel} disabled={pending}>
          Cancel
        </button>
        <button type="button" className="btn ghost sm" onClick={onReset} disabled={pending}>
          Reset form
        </button>
      </div>

      {lastCreated && (
        <div className="info-block" style={{ color: 'var(--ok, #2a7)' }}>
          Last created: <strong>{lastCreated.name}</strong> (slug <code>{lastCreated.slug}</code>,
          validation <code>{lastCreated.validation.status}</code>).
        </div>
      )}
    </>
  );
}
