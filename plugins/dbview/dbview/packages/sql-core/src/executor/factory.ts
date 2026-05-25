import type { SqlDialect } from '@dbview/shared';
import { PostgresExecutor } from './postgres.js';
import { SqliteExecutor } from './sqlite.js';
import { MysqlExecutor } from './mysql.js';
import { MssqlExecutor } from './mssql.js';
import { OracleExecutor } from './oracle.js';
import { ClickhouseExecutor } from './clickhouse.js';
import { DuckdbExecutor } from './duckdb.js';
import type { QueryExecutor } from './types.js';

export function createExecutor(dialect: SqlDialect, connectionString: string): QueryExecutor {
  switch (dialect) {
    case 'postgres':
    case 'cockroach':
      return new PostgresExecutor(connectionString);
    case 'sqlite':
      return new SqliteExecutor(connectionString);
    case 'mysql':
    case 'mariadb':
      return new MysqlExecutor(connectionString);
    case 'mssql':
      return new MssqlExecutor(connectionString);
    case 'oracle':
      return new OracleExecutor(connectionString);
    case 'clickhouse':
      return new ClickhouseExecutor(connectionString);
    case 'duckdb':
      return new DuckdbExecutor(connectionString);
  }
}
