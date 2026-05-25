/**
 * Eval harness contract. Cases describe a NL prompt + grounded expectations
 * over the resulting SQL. The runner is provider-agnostic: it accepts an
 * adapter that returns a JSON envelope string (real Ollama/OpenAI in live
 * mode, canned fixtures in unit tests) so the same harness exercises the
 * prompt builder + sanitize + validator pipeline regardless of LLM source.
 */
export interface EvalExpectation {
  /** Validator and sanitize must accept the query without throwing. */
  mustValidate?: boolean;
  /** Every listed table id MUST appear in the validator's `involvedTables`. */
  mustInvolveTables?: string[];
  /** No table outside this set may appear in `involvedTables`. */
  onlyInvolveTables?: string[];
  /** Substrings the (lowercased) query must contain. */
  mustContain?: string[];
  /** Substrings the (lowercased) query must NOT contain. */
  mustNotContain?: string[];
}

export interface EvalCase {
  id: string;
  prompt: string;
  rowLimit?: number;
  expectations: EvalExpectation;
}

export interface EvalResult {
  caseId: string;
  passed: boolean;
  reasons: string[];
  validatedQuery?: string;
  involvedTables?: string[];
  durationMs: number;
}

export interface RunnerAdapter {
  /**
   * Take a (system, user) chat pair and produce the LLM JSON envelope as a
   * raw string. The runner parses it via the same logic as the production
   * Nl2SqlService so envelope handling stays consistent.
   */
  complete(system: string, user: string): Promise<string>;
}
