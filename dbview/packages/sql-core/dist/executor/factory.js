import { PostgresExecutor } from './postgres.js';
import { SqliteExecutor } from './sqlite.js';
import { MysqlExecutor } from './mysql.js';
import { MssqlExecutor } from './mssql.js';
import { OracleExecutor } from './oracle.js';
import { ClickhouseExecutor } from './clickhouse.js';
import { DuckdbExecutor } from './duckdb.js';
export function createExecutor(dialect, connectionString) {
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
//# sourceMappingURL=factory.js.map