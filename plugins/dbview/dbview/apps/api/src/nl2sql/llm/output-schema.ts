import { z } from 'zod';

/**
 * Zod schema for the JSON envelope every NL2Query LLM call must produce.
 *
 * Mirrors the `LlmJson` interface in nl2sql.service.ts. The remote adapters
 * (OpenAI/Anthropic via the Vercel AI SDK) use `generateObject` with this
 * schema to enforce shape natively at the provider, eliminating the
 * "model emitted prose / fenced code / extra fields" parse-error retries.
 *
 * IMPORTANT — mirroring rule: any change here MUST stay compatible with
 * `parseJsonResponse` in nl2sql.service.ts. The parser is the unified
 * landing path for all adapter outputs (structured + ollama + sqlcoder).
 */
export const Nl2QueryOutputSchema = z.object({
  query: z
    .string()
    .min(1)
    .describe(
      'The generated query in the requested language (SQL / SOQL / Cypher / Qdrant envelope / Mongo envelope / Elasticsearch envelope / Redis command). MUST be a single statement.',
    ),
  language: z
    .enum(['sql', 'soql', 'cypher', 'qdrant', 'mongodb', 'elasticsearch', 'redis'])
    .describe('Identifies how `query` should be interpreted by the executor.'),
  explanation: z
    .string()
    .default('')
    .describe(
      'Plain-language explanation (one or two sentences) of what the query does and why it answers the user question.',
    ),
  joinNotes: z
    .array(z.string())
    .default([])
    .describe(
      'For each JOIN / relationship traversal, a short comment describing the link (e.g. "1 customer -> N orders").',
    ),
  involvedEntities: z
    .array(z.string())
    .default([])
    .describe(
      'List of tables / sObjects / labels / collections / indices the query reads from, exactly as listed in the prompt schema.',
    ),
});

export type Nl2QueryOutput = z.infer<typeof Nl2QueryOutputSchema>;
