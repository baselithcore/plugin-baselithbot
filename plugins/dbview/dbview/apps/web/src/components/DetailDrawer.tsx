import type { UnifiedSchema } from '@dbview/shared';
import { useAppStore } from '../store/app.js';
import { RelationalDetail } from './detail-drawer/RelationalDetail.js';
import { GraphDetail } from './detail-drawer/GraphDetail.js';
import { VectorDetail } from './detail-drawer/VectorDetail.js';

interface Props {
  schema?: UnifiedSchema;
}

export function DetailDrawer({ schema }: Props) {
  const selection = useAppStore((s) => s.detailSelection);
  const close = useAppStore((s) => s.closeDetail);
  const connId = useAppStore((s) => s.activeConnectionId);
  const open = !!selection;

  if (!schema) return null;
  if (schema.kind === 'relational') {
    return (
      <RelationalDetail
        open={open}
        onClose={close}
        connectionId={connId}
        schema={schema}
        tableId={selection?.tableId}
        focusedColumn={selection?.columnName}
      />
    );
  }
  if (schema.kind === 'graph') {
    return (
      <GraphDetail
        open={open}
        onClose={close}
        connectionId={connId}
        schema={schema}
        labelId={selection?.tableId}
        focusedProperty={selection?.columnName}
      />
    );
  }
  if (schema.kind === 'vector') {
    return (
      <VectorDetail
        open={open}
        onClose={close}
        connectionId={connId}
        schema={schema}
        collectionId={selection?.tableId}
      />
    );
  }
  // keyvalue + search + document: no dedicated detail view yet.
  return null;
}
