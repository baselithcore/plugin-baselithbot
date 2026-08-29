import { type PropertyGraphSchema, type SafetyWarning } from '@dbview/shared';
export interface CypherSafetyOptions {
    schema: PropertyGraphSchema;
    rowLimit: number;
    allowWrites: boolean;
}
export interface CypherValidationResult {
    query: string;
    warnings: SafetyWarning[];
    involvedLabels: string[];
}
export declare class CypherSafetyValidator {
    validate(rawQuery: string, opts: CypherSafetyOptions): CypherValidationResult;
}
//# sourceMappingURL=safety.d.ts.map