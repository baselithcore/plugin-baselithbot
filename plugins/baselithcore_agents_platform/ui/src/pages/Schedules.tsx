import { useEffect, useState } from 'react';
import { GlassPanel } from '../components/GlassPanel';
import { Skeleton } from '../components/Skeleton';
import { api } from '../lib/api';
import type { AgentBlueprint, AgentCapability, ScheduleSpec } from '../lib/types';

const INTERVALS = [
  { label: 'every 1m', value: 60 },
  { label: 'every 1h', value: 3600 },
  { label: 'every 8h', value: 28800 },
  { label: 'every 24h', value: 86400 },
];

/** Manage recurring agent runs (e.g. operate every 8h). */
export function Schedules() {
  const [schedules, setSchedules] = useState<ScheduleSpec[] | null>(null);
  const [blueprints, setBlueprints] = useState<AgentBlueprint[]>([]);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    try {
      const [sc, bp] = await Promise.all([api.listSchedules(), api.listBlueprints()]);
      setSchedules(sc);
      setBlueprints(bp);
    } catch (e) {
      setError((e as Error).message);
    }
  }

  useEffect(() => {
    void load();
  }, []);

  if (error)
    return (
      <GlassPanel title="Schedules">
        <p className="text-rose-400">{error}</p>
      </GlassPanel>
    );
  if (!schedules) return <Skeleton height={220} />;

  return (
    <div className="space-y-6">
      <GlassPanel title="New schedule" subtitle="Run an agent capability on a fixed interval.">
        <ScheduleForm blueprints={blueprints} onCreated={load} />
      </GlassPanel>
      <GlassPanel title="Active schedules" subtitle={`${schedules.length} registered`}>
        {schedules.length === 0 ? (
          <p className="text-sm text-slate-400">No schedules yet.</p>
        ) : (
          <div className="space-y-2">
            {schedules.map((s) => (
              <div
                key={s.id}
                className="flex items-center justify-between gap-4 rounded-lg border border-ink-600/50 bg-ink-800/40 px-4 py-2.5"
              >
                <div className="min-w-0">
                  <div className="flex items-center gap-2 text-sm">
                    <span className="font-mono text-slate-300">{s.blueprint_id}</span>
                    <span className="rounded bg-ink-700/70 px-1.5 py-0.5 font-mono text-[10px] text-cyan">
                      {s.capability}
                    </span>
                    <span className="text-[11px] text-slate-500">
                      every {Math.round(s.interval_seconds)}s · {s.runs} run(s)
                    </span>
                  </div>
                  <p className="truncate text-xs text-slate-500">{s.task}</p>
                </div>
                <button
                  onClick={async () => {
                    await api.deleteSchedule(s.id);
                    void load();
                  }}
                  className="shrink-0 text-xs text-rose-400/80 hover:text-rose-300"
                >
                  cancel
                </button>
              </div>
            ))}
          </div>
        )}
      </GlassPanel>
    </div>
  );
}

function ScheduleForm({
  blueprints,
  onCreated,
}: {
  blueprints: AgentBlueprint[];
  onCreated: () => void;
}) {
  const [blueprintId, setBlueprintId] = useState('');
  const [task, setTask] = useState('');
  const [interval, setInterval] = useState(28800);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const selected = blueprints.find((b) => b.id === blueprintId);
  const capability: AgentCapability = selected?.scope.capabilities[0] ?? 'operate';

  async function submit() {
    if (!blueprintId) return;
    setBusy(true);
    setError(null);
    try {
      await api.createSchedule(blueprintId, capability, task, interval);
      setTask('');
      onCreated();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  if (blueprints.length === 0) {
    return <p className="text-sm text-slate-400">Create an agent first in the Builder.</p>;
  }

  return (
    <div className="space-y-3">
      <div className="grid gap-3 sm:grid-cols-2">
        <select
          value={blueprintId}
          onChange={(e) => setBlueprintId(e.target.value)}
          className="rounded-xl border border-ink-600/60 bg-ink-900/60 px-3 py-2 text-sm text-slate-100 outline-none focus:border-iris/50"
        >
          <option value="">Select agent…</option>
          {blueprints.map((b) => (
            <option key={b.id} value={b.id}>
              {b.name} ({b.scope.capabilities[0]})
            </option>
          ))}
        </select>
        <select
          value={interval}
          onChange={(e) => setInterval(Number(e.target.value))}
          className="rounded-xl border border-ink-600/60 bg-ink-900/60 px-3 py-2 text-sm text-slate-100 outline-none focus:border-iris/50"
        >
          {INTERVALS.map((i) => (
            <option key={i.value} value={i.value}>
              {i.label}
            </option>
          ))}
        </select>
      </div>
      <textarea
        value={task}
        onChange={(e) => setTask(e.target.value)}
        rows={2}
        placeholder="Task to run each tick…"
        className="w-full rounded-xl border border-ink-600/60 bg-ink-900/60 p-3 text-sm text-slate-100 outline-none focus:border-iris/50"
      />
      <button
        onClick={submit}
        disabled={busy || !blueprintId || !task.trim()}
        className="rounded-lg bg-gradient-to-r from-iris to-cyan px-4 py-2 text-sm font-semibold text-ink-900 disabled:opacity-40"
      >
        {busy ? 'Scheduling…' : `Schedule (${capability})`}
      </button>
      {error && <p className="text-sm text-rose-400">{error}</p>}
    </div>
  );
}
