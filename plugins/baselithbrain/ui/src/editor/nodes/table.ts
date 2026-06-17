import Table from '@tiptap/extension-table';
import TableRow from '@tiptap/extension-table-row';
import TableHeader from '@tiptap/extension-table-header';
import TableCell from '@tiptap/extension-table-cell';
import type { Node as PMNode } from '@tiptap/pm/model';

// Markdown-it (tiptap-markdown's parser) renders GFM pipe tables to <table>
// HTML, and the Table extension parses that HTML — so parsing is native. Only
// the *serialize* side needs help: prosemirror-markdown has no table writer.

/** Render one cell's inline content to a pipe-safe Markdown string. */
function cellText(state: any, cell: PMNode): string {
  const start = state.out.length;
  const inline = cell.firstChild ?? cell; // cell → paragraph → inline
  state.renderInline(inline);
  const text = state.out.slice(start);
  state.out = state.out.slice(0, start); // rollback; we assemble rows ourselves
  return text.replace(/\n+/g, ' ').replace(/\|/g, '\\|').trim();
}

function rowCells(state: any, row: PMNode): string[] {
  const cells: string[] = [];
  row.forEach((cell) => cells.push(cellText(state, cell)));
  return cells;
}

function serializeTable(state: any, node: PMNode): void {
  const rows: string[][] = [];
  node.forEach((row) => rows.push(rowCells(state, row)));
  if (!rows.length) return;
  const cols = Math.max(...rows.map((r) => r.length));
  const pad = (r: string[]) => Array.from({ length: cols }, (_, i) => r[i] ?? '');
  const [header, ...body] = rows;
  state.write(`| ${pad(header).join(' | ')} |\n`);
  state.write(
    `| ${pad(header)
      .map(() => '---')
      .join(' | ')} |\n`
  );
  for (const r of body) state.write(`| ${pad(r).join(' | ')} |\n`);
  state.closeBlock(node);
}

const markdownStorage = {
  addStorage() {
    return { markdown: { serialize: serializeTable, parse: {} } };
  },
};

export const TableKit = [
  Table.extend(markdownStorage).configure({ resizable: true }),
  TableRow,
  TableHeader,
  TableCell,
];
