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
export declare const Nl2QueryOutputSchema: z.ZodObject<{
    query: z.ZodString;
    language: z.ZodEnum<["sql", "soql", "cypher", "qdrant", "mongodb", "elasticsearch", "redis"]>;
    explanation: z.ZodDefault<z.ZodString>;
    joinNotes: z.ZodDefault<z.ZodArray<z.ZodString, "many">>;
    involvedEntities: z.ZodDefault<z.ZodArray<z.ZodString, "many">>;
}, "strip", z.ZodTypeAny, {
    query: string;
    language: "mongodb" | "qdrant" | "redis" | "elasticsearch" | "sql" | "cypher" | "soql";
    explanation: string;
    joinNotes: string[];
    involvedEntities: string[];
}, {
    query: string;
    language: "mongodb" | "qdrant" | "redis" | "elasticsearch" | "sql" | "cypher" | "soql";
    explanation?: string | undefined;
    joinNotes?: string[] | undefined;
    involvedEntities?: string[] | undefined;
}>;
export type Nl2QueryOutput = z.infer<typeof Nl2QueryOutputSchema>;
//# sourceMappingURL=output-schema.d.ts.map