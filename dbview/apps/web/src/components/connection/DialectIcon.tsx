import {
  SiPostgresql,
  SiMysql,
  SiMariadb,
  SiSqlite,
  SiMongodb,
  SiNeo4J,
  SiCockroachlabs,
  SiRedis,
  SiClickhouse,
  SiDuckdb,
  SiElasticsearch,
  SiSalesforce,
} from 'react-icons/si';
import { Database } from 'lucide-react';
import { DIALECT_META, type Dialect } from '@dbview/shared';
import type { ComponentType, SVGProps } from 'react';
import { SqlServerIcon } from './icons/SqlServerIcon.js';
import { OracleIcon } from './icons/OracleIcon.js';
import { FalkorIcon } from './icons/FalkorIcon.js';
import { QdrantIcon } from './icons/QdrantIcon.js';
import { UltipaIcon } from './icons/UltipaIcon.js';

interface DialectIconProps {
  dialect: Dialect;
  size?: number;
  className?: string;
  /** Render bare brand glyph (no rounded square background). */
  bare?: boolean;
}

type IconCmp = ComponentType<SVGProps<SVGSVGElement> & { size?: number | string; color?: string }>;

const ICON_BY_DIALECT: Record<Dialect, IconCmp | null> = {
  postgres: SiPostgresql as IconCmp,
  mysql: SiMysql as IconCmp,
  mariadb: SiMariadb as IconCmp,
  mssql: SqlServerIcon as IconCmp,
  sqlite: SiSqlite as IconCmp,
  cockroach: SiCockroachlabs as IconCmp,
  oracle: OracleIcon as IconCmp,
  clickhouse: SiClickhouse as IconCmp,
  duckdb: SiDuckdb as IconCmp,
  mongodb: SiMongodb as IconCmp,
  neo4j: SiNeo4J as IconCmp,
  falkordb: FalkorIcon as IconCmp,
  ultipa: UltipaIcon as IconCmp,
  qdrant: QdrantIcon as IconCmp,
  redis: SiRedis as IconCmp,
  elasticsearch: SiElasticsearch as IconCmp,
  salesforce: SiSalesforce as IconCmp,
  'salesforce-data-cloud': SiSalesforce as IconCmp,
};

export function DialectIcon({ dialect, size = 28, className, bare = false }: DialectIconProps) {
  const meta = DIALECT_META[dialect];
  const Icon = ICON_BY_DIALECT[dialect];
  const glyphSize = Math.round(size * (bare ? 1 : 0.62));

  const glyph = Icon ? (
    <Icon size={glyphSize} color={bare ? meta.brandColor : '#fff'} aria-hidden="true" />
  ) : (
    <Database
      width={glyphSize}
      height={glyphSize}
      color={bare ? meta.brandColor : '#fff'}
      strokeWidth={2}
      aria-hidden="true"
    />
  );

  if (bare) {
    return (
      <span
        className={className}
        role="img"
        aria-label={meta.label}
        style={{
          display: 'inline-flex',
          alignItems: 'center',
          justifyContent: 'center',
          width: size,
          height: size,
        }}
      >
        {glyph}
      </span>
    );
  }

  return (
    <span
      className={className}
      role="img"
      aria-label={meta.label}
      style={{
        width: size,
        height: size,
        display: 'inline-flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: meta.brandColor,
        borderRadius: 6,
        boxShadow: 'inset 0 0 0 1px rgb(0 0 0 / 0.15)',
      }}
    >
      {glyph}
    </span>
  );
}
