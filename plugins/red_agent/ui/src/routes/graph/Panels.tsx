import { Link } from 'react-router-dom';
import { SeverityPill } from '../../components/SeverityPill';
import { Icon } from '../../components/ui';
import { EDGE_COLOR } from './styles';
import type { SelectedEdge, SelectedNode } from './types';

export function NodeDetailsPanel(props: {
  node: SelectedNode;
  target: string;
  onClose: () => void;
  onPathToTarget: () => void;
  hasPath: boolean;
}) {
  const { node } = props;
  const isVuln = node.label === 'Vulnerability';
  const priority =
    node.severity === 'critical' || node.severity === 'high' || (node.cvss ?? 0) >= 8.5;
  return (
    <Panel title={node.label} subtitle={node.display} onClose={props.onClose}>
      <div
        className={`mb-4 rounded border px-3 py-2 ${
          priority
            ? 'border-sev-critical/40 bg-sev-critical/10'
            : 'border-bg-line bg-bg-elevated/60'
        }`}
      >
        <p className="font-display text-[10px] uppercase tracking-wider text-text-muted">
          Response priority
        </p>
        <p
          className={`mt-1 font-display text-sm ${priority ? 'text-sev-critical' : 'text-text-primary'}`}
        >
          {priority ? 'Immediate review' : 'Context review'}
        </p>
      </div>

      <dl className="grid grid-cols-3 gap-y-3 text-xs">
        <Row term="Type" value={node.label} />
        {node.severity && (
          <Row term="Severity" valueNode={<SeverityPill severity={node.severity} />} />
        )}
        {node.cvss !== null && <Row term="CVSS" value={node.cvss.toFixed(1)} />}
        <Row term="Edges" value={String(node.neighbors)} />
        <Row term="ID" value={node.id} mono small />
      </dl>

      <div className="mt-6 space-y-2">
        {props.hasPath && (
          <button
            type="button"
            onClick={props.onPathToTarget}
            className="flex w-full items-center justify-center gap-2 rounded border border-accent-warn/40 bg-accent-warn/10 px-4 py-2 font-display text-xs text-accent-warn transition hover:bg-accent-warn/20 focus:outline-none focus-visible:ring-2 focus-visible:ring-accent-warn/40"
          >
            <Icon.Network size={13} />
            Highlight path to target
          </button>
        )}
        {isVuln && props.target && (
          <Link
            to={`/findings?target=${encodeURIComponent(props.target)}`}
            className="flex w-full items-center justify-center gap-2 rounded bg-accent-neon/15 px-4 py-2 text-center font-display text-xs text-accent-neon shadow-glow transition hover:bg-accent-neon/25 focus:outline-none focus-visible:ring-2 focus-visible:ring-brand/40"
          >
            <Icon.Findings size={13} />
            View in findings
          </Link>
        )}
      </div>
    </Panel>
  );
}

export function EdgeDetailsPanel(props: { edge: SelectedEdge; onClose: () => void }) {
  const { edge } = props;
  return (
    <Panel title="Relation" subtitle={edge.type} onClose={props.onClose}>
      <div
        className="mb-4 h-1 w-full rounded"
        style={{ background: EDGE_COLOR[edge.type] ?? '#37445a' }}
        aria-hidden
      />
      <dl className="grid grid-cols-3 gap-y-3 text-xs">
        <Row term="Type" value={edge.type} mono />
        <Row term="From" value={edge.sourceLabel} />
        <Row term="Source" value={edge.source} mono small />
        <Row term="To" value={edge.targetLabel} />
        <Row term="Target" value={edge.target} mono small />
      </dl>
    </Panel>
  );
}

function Panel(props: {
  title: string;
  subtitle: string;
  onClose: () => void;
  children: React.ReactNode;
}) {
  return (
    <aside
      role="dialog"
      aria-label={`details for ${props.subtitle}`}
      className="absolute right-0 top-0 z-30 h-full w-[360px] max-w-[calc(100vw-2rem)] overflow-auto border-l border-bg-line bg-bg-overlay/95 p-5 shadow-elevated backdrop-blur"
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="font-display text-[10px] uppercase tracking-wider text-text-muted">
            {props.title}
          </p>
          <h2 className="mt-1 break-all font-display text-sm text-text-primary">
            {props.subtitle}
          </h2>
        </div>
        <button
          type="button"
          onClick={props.onClose}
          aria-label="close details"
          className="grid h-7 w-7 place-items-center rounded border border-bg-line text-text-muted transition hover:border-bg-line-strong hover:text-text-primary focus:outline-none focus-visible:ring-2 focus-visible:ring-brand/40"
        >
          <Icon.X size={13} />
        </button>
      </div>
      <div className="mt-5">{props.children}</div>
    </aside>
  );
}

function Row(props: {
  term: string;
  value?: string;
  valueNode?: React.ReactNode;
  mono?: boolean;
  small?: boolean;
}) {
  const cls = [
    'col-span-2',
    props.mono ? 'font-display' : 'text-text-primary',
    props.small ? 'break-all text-[11px] text-text-muted' : 'text-text-primary',
  ].join(' ');
  return (
    <>
      <dt className="col-span-1 text-text-muted">{props.term}</dt>
      <dd className={cls}>{props.valueNode ?? props.value ?? '—'}</dd>
    </>
  );
}
