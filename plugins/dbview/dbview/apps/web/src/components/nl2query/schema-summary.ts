import type { UnifiedSchema } from '@dbview/shared';

export interface SchemaMetric {
  label: string;
  value: string;
}

export interface SchemaSummary {
  kind: UnifiedSchema['kind'];
  dialect: string;
  primary: SchemaMetric;
  secondary: SchemaMetric;
  tertiary?: SchemaMetric;
}

const numberFormatter = new Intl.NumberFormat(undefined, { maximumFractionDigits: 0 });

export function summarizeSchema(schema: UnifiedSchema | undefined): SchemaSummary | null {
  if (!schema) return null;

  if (schema.kind === 'relational') {
    const columns = schema.tables.reduce((sum, table) => sum + table.columns.length, 0);
    return {
      kind: schema.kind,
      dialect: schema.dialect,
      primary: metric('tables', schema.tables.length),
      secondary: metric('columns', columns),
      tertiary: metric('relations', schema.edges.length),
    };
  }

  if (schema.kind === 'graph') {
    const properties =
      schema.labels.reduce((sum, label) => sum + label.properties.length, 0) +
      schema.relationships.reduce((sum, relationship) => sum + relationship.properties.length, 0);
    return {
      kind: schema.kind,
      dialect: schema.dialect,
      primary: metric('labels', schema.labels.length),
      secondary: metric('relationships', schema.relationships.length),
      tertiary: metric('properties', properties),
    };
  }

  if (schema.kind === 'document') {
    const fields = schema.collections.reduce(
      (sum, collection) => sum + collection.fields.length,
      0
    );
    const indexes = schema.collections.reduce(
      (sum, collection) => sum + collection.indexes.length,
      0
    );
    return {
      kind: schema.kind,
      dialect: schema.dialect,
      primary: metric('collections', schema.collections.length),
      secondary: metric('fields', fields),
      tertiary: metric('indexes', indexes),
    };
  }

  if (schema.kind === 'vector') {
    const payloadFields = schema.collections.reduce(
      (sum, collection) => sum + collection.payloadFields.length,
      0
    );
    const points = schema.collections.reduce(
      (sum, collection) => sum + (collection.pointCount ?? 0),
      0
    );
    return {
      kind: schema.kind,
      dialect: schema.dialect,
      primary: metric('collections', schema.collections.length),
      secondary: metric('payload fields', payloadFields),
      tertiary: metric('points', points),
    };
  }

  if (schema.kind === 'keyvalue') {
    const types = new Set(schema.namespaces.flatMap((namespace) => namespace.types));
    return {
      kind: schema.kind,
      dialect: schema.dialect,
      primary: metric('keys', schema.totalKeys),
      secondary: metric('namespaces', schema.namespaces.length),
      tertiary: metric('types', types.size),
    };
  }

  const fields = schema.indices.reduce((sum, index) => sum + index.fields.length, 0);
  const aliases = schema.indices.reduce((sum, index) => sum + index.aliases.length, 0);
  return {
    kind: schema.kind,
    dialect: schema.dialect,
    primary: metric('indices', schema.indices.length),
    secondary: metric('fields', fields),
    tertiary: metric('aliases', aliases),
  };
}

export function formatSchemaAge(generatedAt: string | undefined): string | null {
  if (!generatedAt) return null;
  const generated = new Date(generatedAt).getTime();
  if (!Number.isFinite(generated)) return null;

  const minutes = Math.max(0, Math.round((Date.now() - generated) / 60_000));
  if (minutes < 1) return 'just now';
  if (minutes < 60) return `${minutes}m ago`;

  const hours = Math.round(minutes / 60);
  if (hours < 24) return `${hours}h ago`;

  const days = Math.round(hours / 24);
  return `${days}d ago`;
}

function metric(label: string, value: number): SchemaMetric {
  return { label, value: numberFormatter.format(value) };
}
