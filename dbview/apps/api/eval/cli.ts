/* eslint-disable no-console */
/**
 * CLI runner for the NL2Query eval harness.
 *
 *   pnpm --filter @dbview/api eval                       # use ollama default model
 *   EVAL_PROVIDER=openai EVAL_MODEL=gpt-4o-mini pnpm --filter @dbview/api eval
 *   EVAL_PROVIDER=anthropic EVAL_MODEL=claude-sonnet-4-6 pnpm --filter @dbview/api eval
 *
 * The CLI exits 0 when all cases pass, 1 otherwise — wire it into CI as a
 * regression gate when a real LLM endpoint is reachable.
 */
import process from 'node:process';
import { isCodingOllamaModel, type LlmProvider } from '@dbview/shared';
import { createLlmAdapter, defaultModelFor } from '../src/nl2sql/llm/factory.js';
import { SHOP_SCHEMA } from './fixtures/shop-schema.js';
import { SHOP_EVAL_CASES } from './cases/shop-cases.js';
import { renderReport, runEvalCase, summarize } from './runner.js';
import type { RunnerAdapter } from './types.js';

async function main(): Promise<void> {
  const provider = (process.env.EVAL_PROVIDER ?? 'ollama') as LlmProvider;
  const model = process.env.EVAL_MODEL ?? defaultModelFor(provider, 'sql');

  if (provider === 'ollama' && !isCodingOllamaModel(model)) {
    console.warn(
      `[eval] warning: ${model} is not in the curated coding-Ollama allowlist; results may be poor.`,
    );
  }

  console.log(`[eval] provider=${provider} model=${model} cases=${SHOP_EVAL_CASES.length}`);

  const llmAdapter = createLlmAdapter(provider, model);
  const adapter: RunnerAdapter = {
    async complete(system, user) {
      const r = await llmAdapter.complete({ system, user, temperature: 0 }, model);
      return r.text;
    },
  };

  const results = [];
  for (const c of SHOP_EVAL_CASES) {
    const start = Date.now();
    process.stdout.write(`  - ${c.id} ... `);
    const r = await runEvalCase(c, SHOP_SCHEMA, adapter);
    process.stdout.write(`${r.passed ? 'PASS' : 'FAIL'} (${Date.now() - start}ms)\n`);
    results.push(r);
  }

  console.log(`\n${renderReport(results)}`);
  const s = summarize(results);
  process.exit(s.failed === 0 ? 0 : 1);
}

main().catch((err: unknown) => {
  console.error(`[eval] fatal:`, err);
  process.exit(2);
});
