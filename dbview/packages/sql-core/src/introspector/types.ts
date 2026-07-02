import type { SchemaGraph } from '@dbview/shared';

export interface SchemaIntrospector {
  introspect(): Promise<SchemaGraph>;
  close(): Promise<void>;
}
