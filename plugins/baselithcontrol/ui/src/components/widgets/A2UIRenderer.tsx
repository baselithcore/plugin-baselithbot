// Renders the whitelisted A2UI component tree from core/a2a/a2ui.py. Only the
// 12 sealed component types are honored; anything else renders nothing. No raw
// HTML injection — the whitelist is the security boundary, mirrored here.

interface A2UINode {
  type: string;
  text?: string;
  level?: number;
  label?: string;
  tone?: string;
  children?: A2UINode[];
  [key: string]: unknown;
}

const BADGE_TONE: Record<string, string> = {
  neutral: 'bg-slate-400/15 t-dim',
  success: 'bg-emerald-400/15 text-emerald-300',
  warning: 'bg-amber-400/15 text-amber-300',
  danger: 'bg-rose-400/15 text-rose-300',
  info: 'bg-sky-400/15 text-sky-300',
};

function Node({ node }: { node: A2UINode }) {
  const kids = (node.children ?? []).map((c, i) => <Node key={i} node={c} />);
  switch (node.type) {
    case 'container':
    case 'form':
    case 'list':
      return <div className="flex flex-col gap-2">{kids}</div>;
    case 'list_item':
      return <div className="flex items-center gap-2">{kids}</div>;
    case 'heading':
      return <h3 className="text-sm font-semibold t-primary">{node.text}</h3>;
    case 'text':
      return <p className="text-sm t-dim">{node.text}</p>;
    case 'badge':
      return (
        <span
          className={`inline-flex rounded-full px-2 py-0.5 text-xs ${BADGE_TONE[node.tone ?? 'neutral'] ?? BADGE_TONE.neutral}`}
        >
          {node.label ?? node.text}
        </span>
      );
    case 'divider':
      return <hr className="brd" />;
    default:
      return null; // unknown/non-display types are ignored
  }
}

export function A2UIRenderer({ blueprint }: { blueprint: A2UINode | null }) {
  if (!blueprint) return null;
  return <Node node={blueprint} />;
}
