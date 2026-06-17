import { useState } from 'react';
import { GlassPanel } from '../components/GlassPanel';
import { BlueprintCard } from '../components/BlueprintCard';
import { RunPanel } from '../components/RunPanel';
import { api } from '../lib/api';
import type { AgentBlueprint } from '../lib/types';

const EXAMPLES = [
  'An agent that fetches Rome weather and sends it to Telegram',
  'A bug-fixer that repairs failing pytest cases in the sandbox',
  'An agent that explains how the plugin integrity check works',
];

/** Primary surface: turn natural language into a scoped, runnable agent. */
export function Builder() {
  const [description, setDescription] = useState('');
  const [blueprint, setBlueprint] = useState<AgentBlueprint | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function build() {
    setBusy(true);
    setError(null);
    try {
      setBlueprint(await api.createBlueprint(description));
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-6">
      <GlassPanel
        title="Describe your agent"
        subtitle="Plain language in — a scope-bounded, documentation-grounded agent out."
      >
        <textarea
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          rows={4}
          placeholder="e.g. An agent that generates Pydantic models from a JSON schema…"
          className="w-full rounded-xl border border-ink-600/60 bg-ink-900/60 p-3 text-sm text-slate-100 outline-none focus:border-iris/50"
        />
        <div className="mt-3 flex flex-wrap items-center gap-2">
          <button
            onClick={build}
            disabled={busy || description.trim().length < 3}
            className="rounded-lg bg-gradient-to-r from-iris to-cyan px-4 py-2 text-sm font-semibold text-ink-900 disabled:opacity-40"
          >
            {busy ? 'Synthesising…' : 'Create agent'}
          </button>
          {EXAMPLES.map((ex) => (
            <button
              key={ex}
              onClick={() => setDescription(ex)}
              className="rounded-lg bg-ink-700/60 px-3 py-1.5 text-xs text-slate-400 hover:text-slate-200"
            >
              {ex.slice(0, 36)}…
            </button>
          ))}
        </div>
        {error && <p className="mt-3 text-sm text-rose-400">{error}</p>}
      </GlassPanel>

      {blueprint && (
        <div className="grid gap-6 lg:grid-cols-[minmax(0,22rem)_1fr]">
          <GlassPanel title="Blueprint">
            <BlueprintCard blueprint={blueprint} />
            {blueprint.system_directive && (
              <details className="mt-3 text-xs text-slate-400">
                <summary className="cursor-pointer text-slate-300">System directive</summary>
                <p className="mt-2 whitespace-pre-wrap">{blueprint.system_directive}</p>
              </details>
            )}
          </GlassPanel>
          <GlassPanel title="Run a capability" subtitle="Stays within the agent's declared scope.">
            <RunPanel blueprint={blueprint} />
          </GlassPanel>
        </div>
      )}
    </div>
  );
}
