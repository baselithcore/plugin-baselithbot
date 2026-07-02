import type { ExecuteQueryResponse } from '@dbview/shared';

export interface QueryExecutor {
  run(sql: string, rowLimit: number): Promise<ExecuteQueryResponse>;
  close(): Promise<void>;
}
