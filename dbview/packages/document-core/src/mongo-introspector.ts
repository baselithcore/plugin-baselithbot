import {
  IntrospectionError,
  type DocumentCollection,
  type DocumentField,
  type DocumentStoreSchema,
} from '@dbview/shared';
import type { Db, MongoClient } from 'mongodb';
import { createMongoClient } from './mongo-client.js';

const SAMPLE_SIZE = 50;
const MAX_DEPTH = 3;
const SAMPLE_VALUES_PER_FIELD = 5;
const MAX_DISTINCT_SAMPLE_VALUES = 6;

const SYSTEM_COLLECTION_RE = /^(system\.|fs\.)/;

export class MongoIntrospector {
  private client: MongoClient | undefined;
  private database = '';

  constructor(private readonly connectionString: string) {}

  private async getDb(): Promise<Db> {
    if (!this.client) {
      const { client, database } = createMongoClient(this.connectionString);
      this.client = client;
      this.database = database;
      await client.connect();
    }
    return this.client.db(this.database);
  }

  async introspect(): Promise<DocumentStoreSchema> {
    try {
      const db = await this.getDb();
      const collInfos = await db.listCollections({}, { nameOnly: false }).toArray();
      const collections: DocumentCollection[] = [];

      for (const info of collInfos) {
        const name = info.name;
        if (!name || SYSTEM_COLLECTION_RE.test(name)) continue;
        const coll = db.collection(name);
        const [count, statsRaw, indexesRaw, sampleDocs] = await Promise.all([
          coll.estimatedDocumentCount().catch(() => undefined),
          db.command({ collStats: name }).catch(() => null) as Promise<Record<
            string,
            unknown
          > | null>,
          coll.indexes().catch(() => []) as Promise<Array<{ name?: string }>>,
          coll
            .aggregate([{ $sample: { size: SAMPLE_SIZE } }])
            .toArray()
            .catch(() => []),
        ]);
        const fields = buildFieldShape(sampleDocs as Array<Record<string, unknown>>);
        const indexes = indexesRaw.map((i) => i.name ?? '').filter((n) => n && n !== '_id_');
        const sizeBytes =
          statsRaw && typeof statsRaw['size'] === 'number'
            ? (statsRaw['size'] as number)
            : undefined;
        collections.push({
          id: `${this.database}.${name}`,
          database: this.database,
          name,
          docCount: count,
          sizeBytes,
          indexes,
          fields,
        });
      }

      return {
        kind: 'document',
        dialect: 'mongodb',
        database: this.database,
        collections,
        generatedAt: new Date().toISOString(),
      };
    } catch (err) {
      throw new IntrospectionError(
        `MongoDB introspection failed: ${(err as Error).message ?? String(err)}`
      );
    }
  }

  async close(): Promise<void> {
    if (this.client) {
      await this.client.close();
      this.client = undefined;
    }
  }
}

interface FieldStat {
  count: number;
  types: Set<string>;
  values: Set<string>;
}

function buildFieldShape(docs: Array<Record<string, unknown>>): DocumentField[] {
  const stats = new Map<string, FieldStat>();
  for (const d of docs) walk(d, '', stats, 0);
  const total = docs.length || 1;
  const fields: DocumentField[] = [];
  for (const [name, stat] of stats) {
    const distinct = [...stat.values];
    fields.push({
      name,
      types: [...stat.types].sort(),
      presence: Number((stat.count / total).toFixed(2)),
      sampleValues:
        distinct.length <= MAX_DISTINCT_SAMPLE_VALUES && distinct.length > 0
          ? distinct.slice(0, SAMPLE_VALUES_PER_FIELD)
          : undefined,
    });
  }
  fields.sort((a, b) => (b.presence ?? 0) - (a.presence ?? 0));
  return fields;
}

function walk(obj: unknown, prefix: string, out: Map<string, FieldStat>, depth: number): void {
  if (depth > MAX_DEPTH || !obj || typeof obj !== 'object' || Array.isArray(obj)) return;
  for (const [k, v] of Object.entries(obj as Record<string, unknown>)) {
    const path = prefix ? `${prefix}.${k}` : k;
    let stat = out.get(path);
    if (!stat) {
      stat = { count: 0, types: new Set(), values: new Set() };
      out.set(path, stat);
    }
    stat.count += 1;
    stat.types.add(bsonType(v));
    if (typeof v === 'string' && v.length < 64) stat.values.add(v);
    else if (typeof v === 'number' || typeof v === 'boolean') stat.values.add(String(v));
    if (v && typeof v === 'object' && !Array.isArray(v) && !(v instanceof Date)) {
      walk(v, path, out, depth + 1);
    }
  }
}

function bsonType(v: unknown): string {
  if (v === null) return 'null';
  if (Array.isArray(v)) return 'array';
  if (v instanceof Date) return 'date';
  if (typeof v === 'object') {
    const ctor = (v as { constructor?: { name?: string } }).constructor?.name;
    if (ctor === 'ObjectId') return 'objectid';
    if (ctor === 'Decimal128') return 'decimal';
    if (ctor === 'Binary') return 'binary';
    return 'object';
  }
  if (typeof v === 'number') return Number.isInteger(v) ? 'int' : 'double';
  return typeof v;
}
