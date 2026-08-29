import type { Dialect } from '@dbview/shared';
export interface FewShotExample {
    question: string;
    query: string;
    /** Optional one-line note shown above the example to highlight the lesson. */
    note?: string;
}
/**
 * Pick the few-shot bank for a (kind, dialect) pair. Returns an empty array
 * when no curated examples exist — callers must skip rendering rather than
 * fall back to a generic dialect, since cross-dialect examples confuse the
 * model more than they help (e.g. teaching `LIMIT` to a T-SQL prompt).
 */
export declare function pickFewShotExamples(dialect: Dialect): FewShotExample[];
/**
 * Render examples as a single string block ready to append to a system prompt.
 * Returns the empty string when no examples are available so callers can
 * unconditionally concatenate without producing a stray heading.
 */
export declare function renderFewShotBlock(examples: FewShotExample[]): string;
//# sourceMappingURL=few-shot.d.ts.map