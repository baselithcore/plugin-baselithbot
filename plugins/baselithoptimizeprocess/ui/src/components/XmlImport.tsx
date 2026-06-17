import { useState } from 'react';

import { api } from '../api/client';
import type { ProcessGraph } from '../api/types';

interface XmlImportProps {
  onImported: (process: ProcessGraph) => void;
}

const SAMPLE = `<process id="p" name="Sample">
  <startEvent id="s" name="Start"/>
  <userTask id="intake" name="Intake"/>
  <serviceTask id="ship" name="Ship"/>
  <endEvent id="e" name="Done"/>
  <sequenceFlow sourceRef="s" targetRef="intake"/>
  <sequenceFlow sourceRef="intake" targetRef="ship"/>
  <sequenceFlow sourceRef="ship" targetRef="e"/>
</process>`;

/** Import a process from a BPMN 2.0 / generic XML document. */
export function XmlImport({ onImported }: XmlImportProps) {
  const [id, setId] = useState('');
  const [xml, setXml] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit() {
    setError(null);
    setBusy(true);
    try {
      onImported(await api.importProcess(id, xml, []));
      setId('');
      setXml('');
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Import failed');
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-3">
      <label className="block text-[11px] font-medium text-slate-400">
        Process ID
        <input
          className="field mt-1"
          name="xml-process-id"
          autoComplete="off"
          spellCheck={false}
          placeholder="order-fulfillment"
          value={id}
          onChange={(e) => setId(e.target.value)}
        />
      </label>
      <label className="block text-[11px] font-medium text-slate-400">
        BPMN / XML
        <textarea
          className="field mt-1 min-h-[260px] font-mono text-xs"
          name="xml-process-body"
          autoComplete="off"
          spellCheck={false}
          placeholder="Paste BPMN or XML here…"
          value={xml}
          onChange={(e) => setXml(e.target.value)}
        />
      </label>
      <div className="flex flex-wrap items-center gap-2">
        <button className="btn-primary" onClick={submit} disabled={busy || !id || !xml}>
          {busy ? 'Importing…' : 'Import Process'}
        </button>
        <button className="btn-ghost" onClick={() => setXml(SAMPLE)}>
          Load Sample
        </button>
      </div>
      <p className="text-[11px] text-slate-500">
        BPMN tasks, events, gateways and sequence flows are recognised. DOCTYPE/ENTITY declarations
        are rejected for safety.
      </p>
      {error && (
        <p className="text-sm text-sev-critical" aria-live="polite">
          {error}
        </p>
      )}
    </div>
  );
}
