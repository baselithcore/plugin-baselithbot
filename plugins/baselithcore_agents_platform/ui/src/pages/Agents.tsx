import { useEffect, useState } from 'react';
import { GlassPanel } from '../components/GlassPanel';
import { BlueprintCard } from '../components/BlueprintCard';
import { RunPanel } from '../components/RunPanel';
import { Skeleton } from '../components/Skeleton';
import { api } from '../lib/api';
import type { AgentBlueprint } from '../lib/types';

/** Registry view: browse stored agents and run any of them. */
export function Agents() {
  const [blueprints, setBlueprints] = useState<AgentBlueprint[] | null>(null);
  const [selected, setSelected] = useState<AgentBlueprint | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    try {
      const list = await api.listBlueprints();
      setBlueprints(list);
      setSelected((cur) => cur ?? list[0] ?? null);
    } catch (e) {
      setError((e as Error).message);
    }
  }

  useEffect(() => {
    void load();
  }, []);

  async function remove(id: string) {
    await api.deleteBlueprint(id);
    setSelected((cur) => (cur?.id === id ? null : cur));
    void load();
  }

  if (error)
    return (
      <GlassPanel title="Agents">
        <p className="text-rose-400">{error}</p>
      </GlassPanel>
    );
  if (!blueprints) {
    return (
      <div className="grid gap-4">
        <Skeleton height={80} />
        <Skeleton height={160} />
      </div>
    );
  }

  return (
    <div className="grid gap-6 lg:grid-cols-[minmax(0,22rem)_1fr]">
      <GlassPanel title="Registered agents" subtitle={`${blueprints.length} total`}>
        {blueprints.length === 0 ? (
          <p className="text-sm text-slate-400">No agents yet — create one in the Builder.</p>
        ) : (
          <div className="space-y-3">
            {blueprints.map((b) => (
              <BlueprintCard
                key={b.id}
                blueprint={b}
                onSelect={setSelected}
                onDelete={remove}
                active={selected?.id === b.id}
              />
            ))}
          </div>
        )}
      </GlassPanel>
      <GlassPanel title={selected ? `Run · ${selected.name}` : 'Run'}>
        {selected ? (
          <RunPanel blueprint={selected} />
        ) : (
          <p className="text-sm text-slate-400">Select an agent to run a capability.</p>
        )}
      </GlassPanel>
    </div>
  );
}
