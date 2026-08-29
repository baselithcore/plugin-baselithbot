import type { SqlDialect } from '@dbview/shared';
export interface SafetyOptions {
    dialect: SqlDialect;
    allowDml: boolean;
    rowLimit: number;
    knownTables: Set<string>;
    knownColumns: Map<string, Set<string>>;
}
export declare const FORBIDDEN_STATEMENT_TYPES: readonly ["drop", "truncate", "alter", "create", "rename", "grant", "revoke", "set", "use", "replace", "call", "execute"];
export declare const DML_STATEMENT_TYPES: readonly ["insert", "update", "delete", "merge"];
export declare const PARSER_DIALECT: Record<SqlDialect, string>;
//# sourceMappingURL=rules.d.ts.map