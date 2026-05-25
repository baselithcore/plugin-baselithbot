import { useEffect, useState } from 'react';
import type { Severity } from '../../lib/api';
import { Icon } from '../../components/ui';
import { NODE_TYPES, NodeType, SEVERITIES } from './types';
import { NODE_BORDER, SEV_RING } from './styles';

const TYPES_OPEN_KEY = 'red_agent.graph_filters.types_open';

export function FilterBar(props: {
  severities: Set<Severity>;
  onToggleSeverity: (s: Severity) => void;
  types: Set<NodeType>;
  onToggleType: (t: NodeType) => void;
  onClear: () => void;
  onCriticalPreset: () => void;
  onTopologyPreset: () => void;
  hidden: number;
}) {
  const hasFilter = props.severities.size > 0 || props.types.size > 0;
  const [typesOpen, setTypesOpen] = useState(
    () => localStorage.getItem(TYPES_OPEN_KEY) === 'true' || props.types.size > 0
  );

  useEffect(() => {
    localStorage.setItem(TYPES_OPEN_KEY, String(typesOpen));
  }, [typesOpen]);
  return (
    <div className="flex flex-wrap items-center gap-2 rounded-lg border border-bg-line bg-bg-elevated/60 px-3 py-2">
      <div className="mr-1 flex items-center gap-2 pr-2 text-text-muted">
        <Icon.Filter2 size={13} />
        <span className="font-display text-[10px] uppercase tracking-wider">Filters</span>
      </div>

      <PresetButton label="Critical path" onClick={props.onCriticalPreset} />
      <PresetButton label="Topology" onClick={props.onTopologyPreset} />

      <Divider />
      <Group label="Severity">
        {SEVERITIES.map((s) => {
          const on = props.severities.has(s);
          return (
            <Chip
              key={s}
              label={s}
              color={SEV_RING[s] ?? '#6b7a90'}
              on={on}
              onClick={() => props.onToggleSeverity(s)}
            />
          );
        })}
      </Group>
      <Divider />
      <button
        type="button"
        onClick={() => setTypesOpen((v) => !v)}
        aria-expanded={typesOpen}
        className={`inline-flex items-center gap-1.5 rounded border px-2.5 py-1 font-display text-[11px] transition ${
          props.types.size > 0
            ? 'border-accent-neon/50 bg-accent-neon/15 text-accent-neon'
            : 'border-bg-line bg-bg-overlay text-text-secondary hover:border-bg-line-strong hover:text-text-primary'
        }`}
      >
        <Icon.Layers size={12} />
        Types
        {props.types.size > 0 && <span>({props.types.size})</span>}
        <Icon.ChevronDown
          size={12}
          className={`transition-transform ${typesOpen ? 'rotate-180' : ''}`}
        />
      </button>
      <button
        type="button"
        onClick={props.onClear}
        disabled={!hasFilter}
        className="ml-auto rounded border border-bg-line px-2 py-1 font-display text-[10px] uppercase tracking-wider text-text-muted transition hover:border-bg-line-strong hover:text-text-primary disabled:cursor-not-allowed disabled:opacity-40"
      >
        Clear {hasFilter ? `(${props.hidden} hidden)` : ''}
      </button>
      {typesOpen && (
        <div className="basis-full border-t border-bg-line/60 pt-2">
          <Group label="Type">
            {NODE_TYPES.map((t) => {
              const on = props.types.has(t);
              return (
                <Chip
                  key={t}
                  label={t}
                  color={NODE_BORDER[t] ?? '#6b7a90'}
                  on={on}
                  onClick={() => props.onToggleType(t)}
                />
              );
            })}
          </Group>
        </div>
      )}
    </div>
  );
}

function Group({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex flex-wrap items-center gap-1.5">
      <span className="mr-1 font-display text-[10px] uppercase tracking-wider text-text-muted">
        {label}
      </span>
      {children}
    </div>
  );
}

function Divider() {
  return <span aria-hidden className="hidden h-5 w-px bg-bg-line md:inline-block" />;
}

function PresetButton({ label, onClick }: { label: string; onClick: () => void }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="rounded border border-bg-line bg-bg-overlay px-2.5 py-1 font-display text-[11px] text-text-secondary transition hover:border-bg-line-strong hover:text-text-primary"
    >
      {label}
    </button>
  );
}

function Chip(props: { label: string; color: string; on: boolean; onClick: () => void }) {
  return (
    <button
      type="button"
      onClick={props.onClick}
      aria-pressed={props.on}
      className={`inline-flex items-center gap-1.5 rounded border px-2.5 py-1 font-display text-[11px] transition ${
        props.on
          ? 'border-accent-neon/50 bg-accent-neon/15 text-accent-neon'
          : 'border-bg-line bg-bg-elevated text-text-muted hover:text-text-primary'
      }`}
    >
      <span
        aria-hidden
        className="inline-block h-2 w-2 rounded-sm"
        style={{ background: props.color, boxShadow: props.on ? `0 0 6px ${props.color}` : 'none' }}
      />
      <span>{props.label}</span>
    </button>
  );
}
