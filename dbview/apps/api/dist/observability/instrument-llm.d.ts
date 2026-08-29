import type { LlmAdapter } from '../nl2sql/llm/provider.js';
export type LlmMode = 'translate' | 'ask' | 'explain' | 'summarize';
export declare function instrumentLlmAdapter(adapter: LlmAdapter, mode: LlmMode): LlmAdapter;
//# sourceMappingURL=instrument-llm.d.ts.map