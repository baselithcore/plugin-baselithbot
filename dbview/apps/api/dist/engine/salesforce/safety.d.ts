/**
 * SOQL safety validator. SOQL is SQL-like but distinct enough that
 * node-sql-parser cannot parse it correctly. This validator is regex-based.
 *
 * Rules mirror the SQL safety contract:
 *  1. SELECT only — no INSERT/UPDATE/DELETE/UPSERT/MERGE.
 *  2. Never `SELECT *` — enumerate fields explicitly.
 *  3. Single statement — no `;`.
 *  4. FROM target must reference a known sObject (case-insensitive).
 *  5. Auto-inject LIMIT when missing.
 *  6. Single-identifier field references must exist in the FROM target's
 *     field set when `knownFields` is provided.
 *
 * Errors are thrown as `UnsafeSqlError` (shared with the SQL validator) so the
 * NL2SQL retry loop can treat both engines uniformly.
 */
export interface SoqlSafetyOptions {
    rowLimit: number;
    /** Lowercased known sObject names from introspected schema. */
    knownSObjects: Set<string>;
    /**
     * Map of lowercased sObject name → lowercased field-name set. When provided,
     * the validator rejects single-identifier field references not present in
     * the FROM target's field set. Dotted lookup paths (e.g. `Account.Owner.Name`)
     * are not validated — relationship traversal would require full lookup graph.
     */
    knownFields?: Map<string, Set<string>>;
}
export interface SoqlValidationResult {
    query: string;
}
export declare class SalesforceSafetyValidator {
    validate(soql: string, opts: SoqlSafetyOptions): SoqlValidationResult;
}
//# sourceMappingURL=safety.d.ts.map