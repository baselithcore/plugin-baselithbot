import { SqlSafetyValidator } from '@dbview/sql-core';
/**
 * Salesforce Data Cloud SQL safety validator.
 *
 * SDC speaks an ANSI SQL dialect (Trino-derived) that is close enough to
 * PostgreSQL for node-sql-parser to handle the relevant grammar surface
 * (SELECT, WITH, JOIN, GROUP BY, window functions, LIMIT, double-quoted
 * identifiers). We delegate to the shared `SqlSafetyValidator` with
 * `dialect: 'postgres'` and forward the `knownTables`/`knownColumns` derived
 * from the introspected DMO/DLO metadata.
 *
 * Notes:
 *  - SDC names typically end with `__dlm` (Data Model Object), `__dll` (Data
 *    Lake Object) or `__cio` (Calculated Insight Output). These are valid SQL
 *    identifiers, so no special quoting is needed.
 *  - SDC `/api/v2/query` is read-only by API contract — DML is rejected at
 *    the wire level — but we still enforce `allowDml: false` here for defence
 *    in depth and to emit a friendly client-side error before the round trip.
 */
export class SalesforceDataCloudSafetyValidator {
    inner = new SqlSafetyValidator();
    validate(sql, opts) {
        return this.inner.validate(sql, {
            dialect: 'postgres',
            allowDml: false,
            rowLimit: opts.rowLimit,
            knownTables: opts.knownTables,
            knownColumns: opts.knownColumns,
        });
    }
}
//# sourceMappingURL=safety.js.map