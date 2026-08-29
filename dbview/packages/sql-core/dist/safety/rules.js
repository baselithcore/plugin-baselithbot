export const FORBIDDEN_STATEMENT_TYPES = [
    'drop',
    'truncate',
    'alter',
    'create',
    'rename',
    'grant',
    'revoke',
    'set',
    'use',
    'replace',
    'call',
    'execute',
];
export const DML_STATEMENT_TYPES = ['insert', 'update', 'delete', 'merge'];
export const PARSER_DIALECT = {
    postgres: 'postgresql',
    mysql: 'mysql',
    mariadb: 'mariadb',
    mssql: 'transactsql',
    sqlite: 'sqlite',
    cockroach: 'postgresql',
    // db2 parser handles Oracle's `FETCH FIRST n ROWS ONLY`, double-quoted
    // identifiers, and TO_DATE — none of which the postgresql parser supports
    // when the SELECT also lacks LIMIT/OFFSET. Closer to Oracle than postgresql
    // for our read-only validator use case.
    oracle: 'db2',
    clickhouse: 'postgresql',
    duckdb: 'postgresql',
};
//# sourceMappingURL=rules.js.map