import { Plus, Trash2, Users } from 'lucide-react';
import { useEffect, useState } from 'react';

import { api } from '../../api/client';
import type { Resource } from '../../api/types';
import { Field } from '../forms/Field';

interface Draft {
  name: string;
  role: string;
  cost_per_hour: string;
  currency: string;
}

const EMPTY: Draft = { name: '', role: '', cost_per_hour: '', currency: 'EUR' };

/** Manage the tenant's assignable resource pool (role + hourly rate). */
export function ResourcesPanel() {
  const [resources, setResources] = useState<Resource[]>([]);
  const [draft, setDraft] = useState<Draft>(EMPTY);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function refresh() {
    try {
      setResources(await api.listResources());
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not load resources.');
    }
  }

  useEffect(() => {
    void refresh();
  }, []);

  async function create() {
    if (!draft.name.trim()) {
      setError('Give the resource a name.');
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await api.createResource({
        name: draft.name.trim(),
        role: draft.role.trim(),
        cost_per_hour: Number(draft.cost_per_hour) || 0,
        currency: draft.currency.trim().toUpperCase() || 'EUR',
      });
      setDraft(EMPTY);
      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Create failed.');
    } finally {
      setBusy(false);
    }
  }

  async function patch(id: string, change: Partial<Resource>) {
    setResources((prev) => prev.map((r) => (r.id === id ? { ...r, ...change } : r)));
    try {
      await api.updateResource(id, change);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Update failed.');
      void refresh();
    }
  }

  async function remove(resource: Resource) {
    if (!window.confirm(`Delete “${resource.name}”? It will be unassigned from any step.`)) return;
    try {
      await api.deleteResource(resource.id);
      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Delete failed.');
    }
  }

  return (
    <section className="glass p-4">
      <div className="mb-3 flex items-center gap-2.5">
        <span className="grid h-8 w-8 place-items-center rounded-lg bg-accent/10 text-accent-soft">
          <Users size={16} aria-hidden="true" />
        </span>
        <div>
          <h2 className="text-sm font-semibold text-slate-100">Resource Pool</h2>
          <p className="text-xs text-slate-500">
            People, teams or machines. A resource’s rate is the source of truth for any step it’s
            assigned to.
          </p>
        </div>
      </div>

      {error && (
        <p className="mb-3 rounded-lg border border-sev-critical/20 bg-sev-critical/10 px-3 py-2 text-sm text-sev-critical">
          {error}
        </p>
      )}

      <div className="mb-4 grid grid-cols-1 items-end gap-2 sm:grid-cols-[1fr_1fr_7rem_5rem_auto]">
        <Field label="Name" required>
          <input
            className="field"
            autoComplete="off"
            placeholder="Senior Analyst"
            value={draft.name}
            onChange={(e) => setDraft({ ...draft, name: e.target.value })}
          />
        </Field>
        <Field label="Role">
          <input
            className="field"
            autoComplete="off"
            placeholder="Analyst"
            value={draft.role}
            onChange={(e) => setDraft({ ...draft, role: e.target.value })}
          />
        </Field>
        <Field label="Rate" suffix="/h">
          <input
            className="field"
            type="number"
            inputMode="decimal"
            min={0}
            placeholder="0"
            value={draft.cost_per_hour}
            onChange={(e) => setDraft({ ...draft, cost_per_hour: e.target.value })}
          />
        </Field>
        <Field label="Cur.">
          <input
            className="field"
            autoComplete="off"
            value={draft.currency}
            onChange={(e) => setDraft({ ...draft, currency: e.target.value })}
          />
        </Field>
        <button className="btn-primary justify-center" onClick={create} disabled={busy}>
          <Plus size={15} aria-hidden="true" />
          Add
        </button>
      </div>

      {resources.length === 0 ? (
        <p className="text-sm text-slate-500">
          No resources yet. Add one above, then assign it to steps in <b>Edit Map</b>.
        </p>
      ) : (
        <ul className="space-y-1.5">
          {resources.map((r) => (
            <li
              key={r.id}
              className="grid grid-cols-[1fr_1fr_7rem_4rem_auto] items-center gap-2 rounded-lg bg-white/[0.03] px-3 py-2"
            >
              <input
                className="field"
                value={r.name}
                onChange={(e) =>
                  setResources((prev) =>
                    prev.map((x) => (x.id === r.id ? { ...x, name: e.target.value } : x))
                  )
                }
                onBlur={(e) => patch(r.id, { name: e.target.value })}
              />
              <input
                className="field"
                placeholder="role"
                value={r.role}
                onChange={(e) =>
                  setResources((prev) =>
                    prev.map((x) => (x.id === r.id ? { ...x, role: e.target.value } : x))
                  )
                }
                onBlur={(e) => patch(r.id, { role: e.target.value })}
              />
              <input
                className="field"
                type="number"
                min={0}
                value={r.cost_per_hour}
                onChange={(e) =>
                  setResources((prev) =>
                    prev.map((x) =>
                      x.id === r.id ? { ...x, cost_per_hour: Number(e.target.value) } : x
                    )
                  )
                }
                onBlur={(e) => patch(r.id, { cost_per_hour: Number(e.target.value) || 0 })}
                title={`${r.currency}/h`}
              />
              <label className="flex items-center gap-1.5 text-[11px] text-slate-400">
                <input
                  type="checkbox"
                  checked={r.active}
                  onChange={(e) => patch(r.id, { active: e.target.checked })}
                />
                active
              </label>
              <button
                className="btn-danger justify-center"
                onClick={() => remove(r)}
                aria-label={`Delete ${r.name}`}
              >
                <Trash2 size={14} aria-hidden="true" />
              </button>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
