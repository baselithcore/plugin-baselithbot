import { useEffect, useMemo, useState } from 'react';
import { api } from '../../../../lib/api';
import { Chip } from '../../Badge';
import { Icon } from '../../Icon';

const SIGMA_OVERRIDE_KEY = (findingId: string) => `red_agent.sigma.overrides.${findingId}`;

function _loadSigmaOverride(findingId: string): { keywords: string; tags: string } {
  try {
    const raw = localStorage.getItem(SIGMA_OVERRIDE_KEY(findingId));
    if (!raw) return { keywords: '', tags: '' };
    const parsed = JSON.parse(raw) as { keywords?: string; tags?: string };
    return { keywords: parsed.keywords ?? '', tags: parsed.tags ?? '' };
  } catch {
    return { keywords: '', tags: '' };
  }
}

function _saveSigmaOverride(findingId: string, payload: { keywords: string; tags: string }): void {
  try {
    if (!payload.keywords.trim() && !payload.tags.trim()) {
      localStorage.removeItem(SIGMA_OVERRIDE_KEY(findingId));
      return;
    }
    localStorage.setItem(SIGMA_OVERRIDE_KEY(findingId), JSON.stringify(payload));
  } catch {
    /* localStorage may be disabled — ignore */
  }
}

function SigmaDownload({ findingId }: { findingId: string }) {
  const [open, setOpen] = useState(false);
  const initial = useMemo(() => _loadSigmaOverride(findingId), [findingId]);
  const [keywords, setKeywords] = useState(initial.keywords);
  const [tags, setTags] = useState(initial.tags);
  useEffect(() => {
    _saveSigmaOverride(findingId, { keywords, tags });
  }, [findingId, keywords, tags]);
  const customized = Boolean(keywords.trim() || tags.trim());
  const url = api.findingSigmaUrlWithOverrides(findingId, {
    keywords: keywords
      .split('\n')
      .map((s) => s.trim())
      .filter(Boolean),
    tags: tags
      .split(',')
      .map((s) => s.trim())
      .filter(Boolean),
  });
  return (
    <div className="relative">
      <div className="flex items-center gap-1">
        <a
          href={url}
          target="_blank"
          rel="noopener noreferrer"
          download
          className="ra-btn ra-btn-ghost ra-btn-sm"
        >
          <Icon.Download size={12} />
          Sigma rule
          {customized && <Chip tone="brand">edited</Chip>}
        </a>
        <button
          type="button"
          onClick={() => setOpen((x) => !x)}
          className="ra-btn ra-btn-ghost ra-btn-sm px-1.5"
          title="Customize keywords / tags"
        >
          <Icon.ChevronDown
            size={12}
            className={open ? 'rotate-180 transition-transform' : 'transition-transform'}
          />
        </button>
      </div>
      {open && (
        <div className="absolute right-0 z-20 mt-1 w-72 rounded border border-bg-line bg-bg-elevated p-3 shadow-lg">
          <label className="mb-1 block text-2xs font-mono uppercase tracking-wider text-text-muted">
            Keywords (one per line)
          </label>
          <textarea
            value={keywords}
            onChange={(e) => setKeywords(e.target.value)}
            className="ra-input min-h-[80px] font-mono text-2xs"
            placeholder={'UNION SELECT\nOR 1=1'}
          />
          <label className="mt-2 mb-1 block text-2xs font-mono uppercase tracking-wider text-text-muted">
            Tags (comma-separated)
          </label>
          <input
            value={tags}
            onChange={(e) => setTags(e.target.value)}
            className="ra-input font-mono text-2xs"
            placeholder="team.appsec, q2-pentest"
          />
          <div className="mt-2 flex items-center justify-between gap-2">
            <button
              type="button"
              onClick={() => {
                setKeywords('');
                setTags('');
              }}
              className="text-2xs text-text-muted hover:text-text-primary"
              disabled={!customized}
            >
              reset
            </button>
            <a
              href={url}
              target="_blank"
              rel="noopener noreferrer"
              download
              onClick={() => setOpen(false)}
              className="ra-btn ra-btn-primary ra-btn-sm"
            >
              <Icon.Download size={12} />
              Download
            </a>
          </div>
        </div>
      )}
    </div>
  );
}

export function ReplayPanel({
  data,
  isLoading,
  error,
  partial = false,
}: {
  data: import('../../../../lib/api').FindingEvidence | undefined;
  isLoading: boolean;
  error: Error | null;
  partial?: boolean;
}) {
  if (partial) {
    return (
      <div className="rounded border border-bg-line bg-bg-overlay/40 p-4 text-sm text-text-secondary">
        <div className="font-mono text-2xs uppercase tracking-wider text-text-muted">
          Replay unavailable
        </div>
        <p className="mt-2">
          This finding is reconstructed from the attack-surface graph. The relational audit chain is
          not available — likely the scan record was purged or persistence was unavailable when the
          finding was upserted.
        </p>
      </div>
    );
  }
  if (isLoading) {
    return (
      <div className="grid place-items-center py-8 text-sm text-text-muted">
        <span className="font-mono">Loading audit chain…</span>
      </div>
    );
  }
  if (error) {
    return (
      <div className="rounded border border-sev-critical/40 bg-sev-critical/10 p-3 text-sm text-sev-critical">
        {String(error)}
      </div>
    );
  }
  if (!data) {
    return (
      <div className="grid place-items-center py-8 text-sm text-text-muted">
        <span className="font-mono">No replay data.</span>
      </div>
    );
  }
  const tones: Record<string, string> = {
    'scan.roe_violation': 'border-sev-critical/40 bg-sev-critical/10',
    'scan.roe_adjusted': 'border-sev-medium/40 bg-sev-medium/10',
    'scan.critic_veto': 'border-sev-critical/40 bg-sev-critical/10',
    'scan.critic_amended': 'border-sev-medium/40 bg-sev-medium/10',
    'scan.guardrail_violation': 'border-sev-critical/40 bg-sev-critical/10',
    'scan.hitl_denied': 'border-sev-critical/40 bg-sev-critical/10',
    'scan.hitl_timeout': 'border-sev-medium/40 bg-sev-medium/10',
  };
  const sigmaAvailable = Boolean(
    (data.finding.evidence as Record<string, unknown> | undefined)?.detection_guidance
  );
  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between gap-3 text-xs text-text-muted">
        <span>
          Scan <span className="font-mono text-text-primary">{data.scan_id.slice(0, 12)}</span>
        </span>
        <div className="flex items-center gap-3">
          {sigmaAvailable && <SigmaDownload findingId={data.finding.id} />}
          <span className="font-mono">{data.chain.length} events</span>
        </div>
      </div>
      {data.chain.length === 0 ? (
        <div className="rounded border border-bg-line/60 bg-bg-overlay p-3 text-sm text-text-muted">
          No audit events recorded for this scan.
        </div>
      ) : (
        <ol className="space-y-2">
          {data.chain.map((ev) => (
            <li
              key={ev.id}
              className={`rounded border p-3 ${
                tones[ev.event] ?? 'border-bg-line/60 bg-bg-overlay'
              }`}
            >
              <div className="flex items-center justify-between text-xs">
                <span className="font-mono text-text-primary">{ev.event}</span>
                <span className="font-mono text-2xs text-text-muted">
                  {ev.created_at ? new Date(ev.created_at).toLocaleString() : ''}
                </span>
              </div>
              {ev.actor && (
                <div className="mt-1 text-2xs text-text-muted">
                  by <span className="font-mono">{ev.actor}</span>
                </div>
              )}
              {Object.keys(ev.payload ?? {}).length > 0 && (
                <pre className="mt-2 max-h-40 overflow-auto rounded bg-bg-base/60 p-2 font-mono text-2xs leading-snug text-text-secondary">
                  {JSON.stringify(ev.payload, null, 2)}
                </pre>
              )}
            </li>
          ))}
        </ol>
      )}
    </div>
  );
}
