import { PostgresIntrospector } from './postgres.js';
import { SqliteIntrospector } from './sqlite.js';
import { MysqlIntrospector } from './mysql.js';
import { MssqlIntrospector } from './mssql.js';
import { OracleIntrospector } from './oracle.js';
import { ClickhouseIntrospector } from './clickhouse.js';
import { DuckdbIntrospector } from './duckdb.js';
export function createIntrospector(dialect, connectionString) {
    switch (dialect) {
        case 'postgres':
            return new PostgresIntrospector(connectionString, 'postgres');
        case 'cockroach':
            return new PostgresIntrospector(connectionString, 'cockroach');
        case 'sqlite':
            return new SqliteIntrospector(connectionString);
        case 'mysql':
            return new MysqlIntrospector(connectionString, 'mysql');
        case 'mariadb':
            return new MysqlIntrospector(connectionString, 'mariadb');
        case 'mssql':
            return new MssqlIntrospector(connectionString);
        case 'oracle':
            return new OracleIntrospector(connectionString);
        case 'clickhouse':
            return new ClickhouseIntrospector(connectionString);
        case 'duckdb':
            return new DuckdbIntrospector(connectionString);
    }
}
//# sourceMappingURL=factory.js.map