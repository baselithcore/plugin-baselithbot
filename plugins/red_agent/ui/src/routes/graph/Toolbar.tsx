import { FormEvent } from 'react';
import { Icon } from '../../components/ui';
import { SegmentedControl } from './SegmentedControl';
import type { LayoutName, ViewMode } from './types';

export interface Counts {
  nodes: number;
  edges: number;
  critical: number;
  high: number;
  hidden: number;
}

export function Toolbar(props: {
  target: string;
  onTargetChange: (v: string) => void;
  onSubmit: () => void;
  viewMode: ViewMode;
  onViewMode: (v: ViewMode) => void;
  layout: LayoutName;
  onLayout: (v: LayoutName) => void;
  loading: boolean;
  counts: Counts;
  onFit: () => void;
  onReset: () => void;
  onExport: () => void;
  onClear: () => void;
  hasData: boolean;
  graphQuery: string;
  onGraphQueryChange: (v: string) => void;
  graphMatches: number;
  onFocusGraphMatch: () => void;
}) {
  function submit(e: FormEvent) {
    e.preventDefault();
    props.onSubmit();
  }
  return (
    <header className="flex flex-wrap items-start gap-3">
      <div>
        <p className="ra-section-title">Attack graph</p>
        <h1 className="mt-1 font-display text-2xl text-text-primary">Security Graph</h1>
        <p className="mt-1 text-xs text-text-muted">
          Exposure topology, vulnerable paths, and enrichment context.
        </p>
      </div>

      <div className="ml-auto flex flex-wrap items-center gap-2">
        <form
          onSubmit={submit}
          className="flex min-w-[320px] flex-1 items-center gap-2"
          role="search"
        >
          <label className="sr-only" htmlFor="ra-target">
            target value
          </label>
          <div className="relative min-w-[280px] flex-1">
            <Icon.Target
              size={14}
              className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-text-muted"
            />
            <input
              id="ra-target"
              value={props.target}
              onChange={(e) => props.onTargetChange(e.target.value)}
              placeholder="target value (URL or host)"
              className="ra-input h-9 pl-9 font-display text-xs"
            />
          </div>
          <button
            type="submit"
            disabled={!props.target || props.loading}
            className="ra-btn ra-btn-primary h-9 font-display text-xs"
          >
            {props.loading ? 'loading...' : 'Load'}
          </button>
          {props.hasData && (
            <IconButton onClick={props.onClear} label="Clear graph" icon={<Icon.X size={14} />} />
          )}
        </form>

        <div className="relative min-w-[240px]">
          <Icon.Search
            size={14}
            className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-text-muted"
          />
          <input
            id="ra-graph-search"
            value={props.graphQuery}
            onChange={(e) => props.onGraphQueryChange(e.target.value)}
            disabled={!props.hasData}
            placeholder="search graph nodes"
            className="ra-input h-9 pl-9 pr-14 font-display text-xs disabled:opacity-40"
          />
          {props.graphQuery && (
            <button
              type="button"
              onClick={props.onFocusGraphMatch}
              disabled={props.graphMatches === 0}
              className="absolute right-2 top-1/2 -translate-y-1/2 rounded border border-bg-line px-1.5 py-0.5 font-display text-[10px] text-text-muted hover:text-text-primary disabled:opacity-40"
            >
              {props.graphMatches}
            </button>
          )}
        </div>

        <SegmentedControl
          ariaLabel="view mode"
          value={props.viewMode}
          onChange={props.onViewMode}
          options={[
            { value: 'graph', label: '2D' },
            { value: 'graph3d', label: '3D' },
            { value: 'table', label: 'Table' },
          ]}
        />

        <select
          value={props.layout}
          onChange={(e) => props.onLayout(e.target.value as LayoutName)}
          className="ra-select h-9 w-[150px] font-display text-xs"
          aria-label="layout"
        >
          <option value="fcose">Risk map</option>
          <option value="concentric">Blast radius</option>
          <option value="breadthfirst">Attack chain</option>
        </select>

        <IconButton
          onClick={props.onFit}
          disabled={!props.hasData}
          label="Fit graph"
          icon={<Icon.Eye size={14} />}
        />
        <IconButton
          onClick={props.onReset}
          disabled={!props.hasData}
          label="Re-layout graph"
          icon={<Icon.Refresh size={14} />}
        />
        <IconButton
          onClick={props.onExport}
          disabled={!props.hasData}
          label="Export PNG"
          icon={<Icon.Download size={14} />}
        />

        {props.counts.nodes > 0 && (
          <div
            className="flex h-9 items-center gap-2 rounded border border-bg-line bg-bg-elevated/80 px-3 font-display text-xs text-text-muted"
            aria-live="polite"
          >
            <span>
              {props.counts.nodes - props.counts.hidden}/{props.counts.nodes} nodes
            </span>
            <span className="text-text-subtle">/</span>
            <span>{props.counts.edges} edges</span>
            {props.counts.critical > 0 && (
              <>
                <span className="text-text-subtle">/</span>
                <span className="text-sev-critical">{props.counts.critical} critical</span>
              </>
            )}
            {props.counts.high > 0 && (
              <>
                <span className="text-text-subtle">/</span>
                <span className="text-sev-high">{props.counts.high} high</span>
              </>
            )}
          </div>
        )}
      </div>
    </header>
  );
}

function IconButton({
  onClick,
  disabled,
  label,
  icon,
}: {
  onClick: () => void;
  disabled?: boolean;
  label: string;
  icon: React.ReactNode;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      title={label}
      aria-label={label}
      className="grid h-9 w-9 place-items-center rounded-md border border-bg-line bg-bg-elevated/80 text-text-muted transition hover:border-bg-line-strong hover:bg-bg-hover hover:text-text-primary focus:outline-none focus-visible:ring-2 focus-visible:ring-brand/40 disabled:cursor-not-allowed disabled:opacity-40"
    >
      {icon}
    </button>
  );
}
