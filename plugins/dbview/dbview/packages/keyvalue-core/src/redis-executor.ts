import type { ExecuteQueryResponse } from '@dbview/shared';
import type { Redis as RedisClient } from 'ioredis';
import { createRedisClient } from './redis-client.js';
import { validateRedisCommand } from './safety.js';

/**
 * Executes a single read-only Redis command. Input is a plain Redis CLI line
 * (e.g. `HGETALL user:1` or `SCAN 0 MATCH user:* COUNT 100`).
 * Response is shaped into the unified columns/rows envelope so the UI can render
 * tabularly, regardless of native Redis reply type.
 */
export class RedisExecutor {
  private client: RedisClient | undefined;

  constructor(private readonly connectionString: string) {}

  private getClient(): RedisClient {
    if (!this.client) {
      this.client = createRedisClient(this.connectionString).client;
    }
    return this.client;
  }

  async run(query: string, rowLimit: number): Promise<ExecuteQueryResponse> {
    const start = performance.now();
    const { parsed } = validateRedisCommand(query);
    const client = this.getClient();
    if (
      (client.status === 'wait' || client.status === 'end') &&
      typeof client.connect === 'function'
    ) {
      await client.connect();
    }
    const reply = await (
      client as unknown as {
        call: (cmd: string, ...args: string[]) => Promise<unknown>;
      }
    ).call(parsed.command, ...parsed.args);
    const { columns, rows } = shapeReply(parsed.command, reply);
    const truncated = rows.length > rowLimit;
    return {
      columns,
      rows: rows.slice(0, rowLimit),
      rowCount: Math.min(rows.length, rowLimit),
      durationMs: Math.round(performance.now() - start),
      truncated,
    };
  }

  async close(): Promise<void> {
    if (this.client) {
      await this.client.quit().catch(() => undefined);
      this.client = undefined;
    }
  }
}

function shapeReply(command: string, reply: unknown): { columns: string[]; rows: unknown[][] } {
  if (reply === null || reply === undefined) {
    return { columns: ['value'], rows: [[null]] };
  }
  // HGETALL → flat [field1, val1, field2, val2 …] in ioredis; pivot to rows.
  if (command === 'HGETALL' && Array.isArray(reply)) {
    const rows: unknown[][] = [];
    for (let i = 0; i + 1 < reply.length; i += 2) {
      rows.push([reply[i], reply[i + 1]]);
    }
    return { columns: ['field', 'value'], rows };
  }
  if (Array.isArray(reply)) {
    // Nested arrays: render as JSON in single column.
    if (reply.some((r) => Array.isArray(r))) {
      return { columns: ['value'], rows: reply.map((r) => [JSON.stringify(r)]) };
    }
    return { columns: ['value'], rows: reply.map((v) => [v]) };
  }
  if (typeof reply === 'object') {
    return { columns: ['value'], rows: [[JSON.stringify(reply)]] };
  }
  return { columns: ['value'], rows: [[reply]] };
}
