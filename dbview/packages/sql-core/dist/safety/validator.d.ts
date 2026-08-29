import { type SafetyWarning, type SchemaGraph } from '@dbview/shared';
import { type SafetyOptions } from './rules.js';
export interface ValidationResult {
    sql: string;
    warnings: SafetyWarning[];
    involvedTables: string[];
}
export declare class SqlSafetyValidator {
    private readonly parser;
    validate(rawSql: string, opts: SafetyOptions): ValidationResult;
}
export interface KnownSets {
    knownTables: Set<string>;
    knownColumns: Map<string, Set<string>>;
}
export declare function buildKnownSets(graph: SchemaGraph): KnownSets;
export declare function buildKnownSetsMemoized(graph: SchemaGraph): KnownSets;
//# sourceMappingURL=validator.d.ts.map