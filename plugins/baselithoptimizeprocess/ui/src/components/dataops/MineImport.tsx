import { Database, Download, FileSearch } from 'lucide-react';
import { useState } from 'react';

import { api } from '../../api/client';
import type { ProcessGraph } from '../../api/types';
import { parseEventLog, SAMPLE_EVENT_LOG } from '../../lib/eventlog';
import { slugify } from '../../lib/ui';
import { Field } from '../forms/Field';

interface MineImportProps {
  onMined: (process: ProcessGraph) => void;
}

/** Discover a process from a raw event log (process mining). */
export function MineImport({ onMined }: MineImportProps) {
  const [id, setId] = useState('');
  const [idEdited, setIdEdited] = useState(false);
  const [name, setName] = useState('');
  const [text, setText] = useState('');
  const [url, setUrl] = useState('');
  const [minFreq, setMinFreq] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  function onNameChange(value: string) {
    setName(value);
    if (!idEdited) setId(slugify(value));
  }

  async function mine() {
    setError(null);
    setBusy(true);
    try {
      const events = parseEventLog(text);
      if (events.length === 0) throw new Error('No events parsed.');
      const result = await api.mineEventLog(id, name, events, minFreq);
      const process = await api.getProcess(result.process_id);
      onMined(process);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Mining failed');
    } finally {
      setBusy(false);
    }
  }

  async function pull() {
    setError(null);
    setBusy(true);
    try {
      if (!id || !url) throw new Error('A name and a source URL are required.');
      await api.pullSource(id, url, 'events', name, minFreq);
      onMined(await api.getProcess(id));
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Pull failed');
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        <Field label="Process name" required hint="A clear business name for the discovered flow.">
          <input
            className="field"
            name="mined-process-name"
            autoComplete="off"
            placeholder="Order Fulfillment"
            value={name}
            onChange={(e) => onNameChange(e.target.value)}
          />
        </Field>
        <Field label="Identifier" hint="Auto-filled from the name.">
          <input
            className="field font-mono text-xs"
            name="mined-process-id"
            autoComplete="off"
            spellCheck={false}
            placeholder="order-fulfillment"
            value={id}
            onChange={(e) => {
              setIdEdited(true);
              setId(slugify(e.target.value));
            }}
          />
        </Field>
      </div>

      <Field
        label="Event log"
        required
        hint="One row per event: case id, activity, timestamp. CSV or JSON array."
      >
        <textarea
          className="field min-h-[240px] font-mono text-xs"
          name="mined-event-log"
          autoComplete="off"
          spellCheck={false}
          placeholder={'case_id,activity,timestamp\n1001,Receive order,2026-01-01T09:00:00Z'}
          value={text}
          onChange={(e) => setText(e.target.value)}
        />
      </Field>

      <div className="flex flex-wrap items-center gap-2">
        <button className="btn-primary" onClick={mine} disabled={busy || !id || !text}>
          <Database size={15} aria-hidden="true" />
          {busy ? 'Discovering…' : 'Discover Process'}
        </button>
        <button className="btn-ghost" onClick={() => setText(SAMPLE_EVENT_LOG)}>
          <FileSearch size={15} aria-hidden="true" />
          Load sample log
        </button>
        <Field label="Ignore rare activities" suffix="min count" className="ml-auto w-44">
          <input
            type="number"
            min={0}
            className="field"
            placeholder="0"
            value={minFreq}
            onChange={(e) => setMinFreq(Number(e.target.value) || 0)}
          />
        </Field>
      </div>

      <details className="rounded-lg border border-white/[0.08] bg-white/[0.02] p-3">
        <summary className="cursor-pointer text-xs font-medium text-slate-300">
          Or pull the log from a URL
        </summary>
        <div className="mt-3 flex items-end gap-2">
          <Field
            label="Source URL"
            hint="A reachable CSV/JSON endpoint."
            className="min-w-0 flex-1"
          >
            <input
              className="field"
              name="event-log-source-url"
              type="url"
              inputMode="url"
              autoComplete="off"
              placeholder="https://example.com/events.csv"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
            />
          </Field>
          <button className="btn-ghost" onClick={pull} disabled={busy || !id || !url}>
            <Download size={15} aria-hidden="true" />
            {busy ? 'Pulling…' : 'Pull & discover'}
          </button>
        </div>
      </details>

      <p className="text-[11px] leading-relaxed text-slate-500">
        The miner reconstructs the directly-follows graph, ranks path variants, and derives
        cycle-time metrics — the process is monitored immediately after discovery.
      </p>
      {error && (
        <p className="text-sm text-sev-critical" aria-live="polite">
          {error}
        </p>
      )}
    </div>
  );
}
