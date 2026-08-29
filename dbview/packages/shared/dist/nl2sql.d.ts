import { z } from 'zod';
export declare const LlmProviderSchema: z.ZodEnum<["ollama", "openai", "anthropic"]>;
export type LlmProvider = z.infer<typeof LlmProviderSchema>;
/**
 * Providers that authenticate via a per-user API key managed through the
 * settings UI. Ollama is excluded — it is a deployment-level resource
 * configured via `OLLAMA_BASE_URL` and shared across all users.
 */
export declare const RemoteLlmProviderSchema: z.ZodEnum<["openai", "anthropic"]>;
export type RemoteLlmProvider = z.infer<typeof RemoteLlmProviderSchema>;
export declare function isRemoteLlmProvider(p: LlmProvider): p is RemoteLlmProvider;
export declare function isIncompatibleOllamaModel(name: string): boolean;
export declare function isSqlcoderModel(name: string): boolean;
export declare function isCodingOllamaModel(name: string): boolean;
export declare const QueryLanguageSchema: z.ZodEnum<["sql", "cypher", "qdrant", "soql"]>;
export type QueryLanguage = z.infer<typeof QueryLanguageSchema>;
/**
 * Natural-language locale used for assistant prose (summary + explanation).
 * The generated query itself is always SQL/Cypher/Qdrant — locale only
 * affects the user-visible narrative.
 */
export declare const ResponseLocaleSchema: z.ZodEnum<["en", "it"]>;
export type ResponseLocale = z.infer<typeof ResponseLocaleSchema>;
/**
 * Compact record of a prior conversation turn, replayed back to the LLM so
 * follow-up prompts can resolve anaphora ("now group by month", "only Italy",
 * "the previous one"). Only metadata is sent — never the result rows — to
 * keep the prompt budget bounded and avoid leaking row content into the model.
 */
export declare const Nl2ConversationTurnSchema: z.ZodObject<{
    prompt: z.ZodString;
    query: z.ZodOptional<z.ZodString>;
    language: z.ZodOptional<z.ZodEnum<["sql", "cypher", "qdrant", "soql"]>>;
    rowCount: z.ZodOptional<z.ZodNullable<z.ZodNumber>>;
    ok: z.ZodOptional<z.ZodBoolean>;
}, "strip", z.ZodTypeAny, {
    prompt: string;
    query?: string | undefined;
    language?: "qdrant" | "sql" | "cypher" | "soql" | undefined;
    rowCount?: number | null | undefined;
    ok?: boolean | undefined;
}, {
    prompt: string;
    query?: string | undefined;
    language?: "qdrant" | "sql" | "cypher" | "soql" | undefined;
    rowCount?: number | null | undefined;
    ok?: boolean | undefined;
}>;
export type Nl2ConversationTurn = z.infer<typeof Nl2ConversationTurnSchema>;
/** Max prior turns accepted per request — cap is a hard prompt-budget guard. */
export declare const NL2_HISTORY_MAX_TURNS = 6;
export declare const Nl2SqlRequestSchema: z.ZodObject<{
    connectionId: z.ZodString;
    prompt: z.ZodString;
    provider: z.ZodDefault<z.ZodEnum<["ollama", "openai", "anthropic"]>>;
    model: z.ZodOptional<z.ZodString>;
    allowDml: z.ZodDefault<z.ZodBoolean>;
    rowLimit: z.ZodDefault<z.ZodNumber>;
    locale: z.ZodDefault<z.ZodEnum<["en", "it"]>>;
    history: z.ZodDefault<z.ZodArray<z.ZodObject<{
        prompt: z.ZodString;
        query: z.ZodOptional<z.ZodString>;
        language: z.ZodOptional<z.ZodEnum<["sql", "cypher", "qdrant", "soql"]>>;
        rowCount: z.ZodOptional<z.ZodNullable<z.ZodNumber>>;
        ok: z.ZodOptional<z.ZodBoolean>;
    }, "strip", z.ZodTypeAny, {
        prompt: string;
        query?: string | undefined;
        language?: "qdrant" | "sql" | "cypher" | "soql" | undefined;
        rowCount?: number | null | undefined;
        ok?: boolean | undefined;
    }, {
        prompt: string;
        query?: string | undefined;
        language?: "qdrant" | "sql" | "cypher" | "soql" | undefined;
        rowCount?: number | null | undefined;
        ok?: boolean | undefined;
    }>, "many">>;
}, "strip", z.ZodTypeAny, {
    prompt: string;
    connectionId: string;
    provider: "ollama" | "openai" | "anthropic";
    allowDml: boolean;
    rowLimit: number;
    locale: "en" | "it";
    history: {
        prompt: string;
        query?: string | undefined;
        language?: "qdrant" | "sql" | "cypher" | "soql" | undefined;
        rowCount?: number | null | undefined;
        ok?: boolean | undefined;
    }[];
    model?: string | undefined;
}, {
    prompt: string;
    connectionId: string;
    provider?: "ollama" | "openai" | "anthropic" | undefined;
    model?: string | undefined;
    allowDml?: boolean | undefined;
    rowLimit?: number | undefined;
    locale?: "en" | "it" | undefined;
    history?: {
        prompt: string;
        query?: string | undefined;
        language?: "qdrant" | "sql" | "cypher" | "soql" | undefined;
        rowCount?: number | null | undefined;
        ok?: boolean | undefined;
    }[] | undefined;
}>;
export type Nl2SqlRequest = z.infer<typeof Nl2SqlRequestSchema>;
export declare const OllamaModelSchema: z.ZodObject<{
    name: z.ZodString;
    size: z.ZodOptional<z.ZodNumber>;
    digest: z.ZodOptional<z.ZodString>;
    modifiedAt: z.ZodOptional<z.ZodString>;
    family: z.ZodOptional<z.ZodString>;
    parameterSize: z.ZodOptional<z.ZodString>;
}, "strip", z.ZodTypeAny, {
    name: string;
    size?: number | undefined;
    digest?: string | undefined;
    modifiedAt?: string | undefined;
    family?: string | undefined;
    parameterSize?: string | undefined;
}, {
    name: string;
    size?: number | undefined;
    digest?: string | undefined;
    modifiedAt?: string | undefined;
    family?: string | undefined;
    parameterSize?: string | undefined;
}>;
export type OllamaModel = z.infer<typeof OllamaModelSchema>;
export declare const OllamaModelsResponseSchema: z.ZodObject<{
    baseUrl: z.ZodString;
    models: z.ZodArray<z.ZodObject<{
        name: z.ZodString;
        size: z.ZodOptional<z.ZodNumber>;
        digest: z.ZodOptional<z.ZodString>;
        modifiedAt: z.ZodOptional<z.ZodString>;
        family: z.ZodOptional<z.ZodString>;
        parameterSize: z.ZodOptional<z.ZodString>;
    }, "strip", z.ZodTypeAny, {
        name: string;
        size?: number | undefined;
        digest?: string | undefined;
        modifiedAt?: string | undefined;
        family?: string | undefined;
        parameterSize?: string | undefined;
    }, {
        name: string;
        size?: number | undefined;
        digest?: string | undefined;
        modifiedAt?: string | undefined;
        family?: string | undefined;
        parameterSize?: string | undefined;
    }>, "many">;
}, "strip", z.ZodTypeAny, {
    baseUrl: string;
    models: {
        name: string;
        size?: number | undefined;
        digest?: string | undefined;
        modifiedAt?: string | undefined;
        family?: string | undefined;
        parameterSize?: string | undefined;
    }[];
}, {
    baseUrl: string;
    models: {
        name: string;
        size?: number | undefined;
        digest?: string | undefined;
        modifiedAt?: string | undefined;
        family?: string | undefined;
        parameterSize?: string | undefined;
    }[];
}>;
export type OllamaModelsResponse = z.infer<typeof OllamaModelsResponseSchema>;
/**
 * Remote-provider model descriptor surfaced to the UI. Only the `id` is
 * required — extra fields are best-effort metadata for grouping/sorting.
 */
export declare const RemoteModelSchema: z.ZodObject<{
    id: z.ZodString;
    displayName: z.ZodOptional<z.ZodString>;
    family: z.ZodOptional<z.ZodString>;
    /** ISO-8601 timestamp from the provider when available. */
    createdAt: z.ZodOptional<z.ZodString>;
    contextWindow: z.ZodOptional<z.ZodNumber>;
}, "strip", z.ZodTypeAny, {
    id: string;
    displayName?: string | undefined;
    createdAt?: string | undefined;
    family?: string | undefined;
    contextWindow?: number | undefined;
}, {
    id: string;
    displayName?: string | undefined;
    createdAt?: string | undefined;
    family?: string | undefined;
    contextWindow?: number | undefined;
}>;
export type RemoteModel = z.infer<typeof RemoteModelSchema>;
export declare const RemoteModelsResponseSchema: z.ZodObject<{
    provider: z.ZodEnum<["openai", "anthropic"]>;
    models: z.ZodArray<z.ZodObject<{
        id: z.ZodString;
        displayName: z.ZodOptional<z.ZodString>;
        family: z.ZodOptional<z.ZodString>;
        /** ISO-8601 timestamp from the provider when available. */
        createdAt: z.ZodOptional<z.ZodString>;
        contextWindow: z.ZodOptional<z.ZodNumber>;
    }, "strip", z.ZodTypeAny, {
        id: string;
        displayName?: string | undefined;
        createdAt?: string | undefined;
        family?: string | undefined;
        contextWindow?: number | undefined;
    }, {
        id: string;
        displayName?: string | undefined;
        createdAt?: string | undefined;
        family?: string | undefined;
        contextWindow?: number | undefined;
    }>, "many">;
    /** Source of the key used to fetch: 'stored' (per-user) or 'env' fallback. */
    source: z.ZodEnum<["stored", "env"]>;
}, "strip", z.ZodTypeAny, {
    provider: "openai" | "anthropic";
    models: {
        id: string;
        displayName?: string | undefined;
        createdAt?: string | undefined;
        family?: string | undefined;
        contextWindow?: number | undefined;
    }[];
    source: "stored" | "env";
}, {
    provider: "openai" | "anthropic";
    models: {
        id: string;
        displayName?: string | undefined;
        createdAt?: string | undefined;
        family?: string | undefined;
        contextWindow?: number | undefined;
    }[];
    source: "stored" | "env";
}>;
export type RemoteModelsResponse = z.infer<typeof RemoteModelsResponseSchema>;
/**
 * Status payload for `GET /api/llm/providers/:provider/credential`.
 * Plaintext is never returned. `maskedTail` shows the last 4 chars so
 * the user can recognize which key is stored without exposing the secret.
 */
export declare const LlmCredentialStatusSchema: z.ZodObject<{
    provider: z.ZodEnum<["openai", "anthropic"]>;
    hasKey: z.ZodBoolean;
    /** True when the resolved key comes from `OPENAI_API_KEY`/`ANTHROPIC_API_KEY`. */
    envFallback: z.ZodBoolean;
    maskedTail: z.ZodOptional<z.ZodString>;
    updatedAt: z.ZodOptional<z.ZodString>;
}, "strip", z.ZodTypeAny, {
    provider: "openai" | "anthropic";
    hasKey: boolean;
    envFallback: boolean;
    maskedTail?: string | undefined;
    updatedAt?: string | undefined;
}, {
    provider: "openai" | "anthropic";
    hasKey: boolean;
    envFallback: boolean;
    maskedTail?: string | undefined;
    updatedAt?: string | undefined;
}>;
export type LlmCredentialStatus = z.infer<typeof LlmCredentialStatusSchema>;
/**
 * Central LLM-governance state for one pipeline scope.
 *
 * When the BaselithCore host operator pins this plugin's LLM provider/model
 * from the central auth console, the pin is *enforced*: it overrides the
 * per-request provider/model and any per-user BYOK credential, and the UI
 * hides the corresponding controls. `enforced=false` means the scope is
 * ungoverned and the user's own choices apply (default behaviour).
 */
export declare const LlmGovernanceScopeSchema: z.ZodObject<{
    enforced: z.ZodBoolean;
    /** The provider the pin forces, or `null` when not enforced. */
    provider: z.ZodNullable<z.ZodEnum<["ollama", "openai", "anthropic"]>>;
}, "strip", z.ZodTypeAny, {
    provider: "ollama" | "openai" | "anthropic" | null;
    enforced: boolean;
}, {
    provider: "ollama" | "openai" | "anthropic" | null;
    enforced: boolean;
}>;
export type LlmGovernanceScope = z.infer<typeof LlmGovernanceScopeSchema>;
/** Response for `GET /api/llm/governance`. */
export declare const LlmGovernanceStateSchema: z.ZodObject<{
    /** True when any pipeline scope is centrally enforced. */
    enforced: z.ZodBoolean;
    /** NL→Query translation pipeline. */
    translate: z.ZodObject<{
        enforced: z.ZodBoolean;
        /** The provider the pin forces, or `null` when not enforced. */
        provider: z.ZodNullable<z.ZodEnum<["ollama", "openai", "anthropic"]>>;
    }, "strip", z.ZodTypeAny, {
        provider: "ollama" | "openai" | "anthropic" | null;
        enforced: boolean;
    }, {
        provider: "ollama" | "openai" | "anthropic" | null;
        enforced: boolean;
    }>;
    /** Explain/summarize pipeline. */
    explain: z.ZodObject<{
        enforced: z.ZodBoolean;
        /** The provider the pin forces, or `null` when not enforced. */
        provider: z.ZodNullable<z.ZodEnum<["ollama", "openai", "anthropic"]>>;
    }, "strip", z.ZodTypeAny, {
        provider: "ollama" | "openai" | "anthropic" | null;
        enforced: boolean;
    }, {
        provider: "ollama" | "openai" | "anthropic" | null;
        enforced: boolean;
    }>;
}, "strip", z.ZodTypeAny, {
    enforced: boolean;
    translate: {
        provider: "ollama" | "openai" | "anthropic" | null;
        enforced: boolean;
    };
    explain: {
        provider: "ollama" | "openai" | "anthropic" | null;
        enforced: boolean;
    };
}, {
    enforced: boolean;
    translate: {
        provider: "ollama" | "openai" | "anthropic" | null;
        enforced: boolean;
    };
    explain: {
        provider: "ollama" | "openai" | "anthropic" | null;
        enforced: boolean;
    };
}>;
export type LlmGovernanceState = z.infer<typeof LlmGovernanceStateSchema>;
/** Body for `PUT /api/llm/providers/:provider/credential`. */
export declare const SetLlmCredentialSchema: z.ZodObject<{
    apiKey: z.ZodString;
}, "strip", z.ZodTypeAny, {
    apiKey: string;
}, {
    apiKey: string;
}>;
export type SetLlmCredentialRequest = z.infer<typeof SetLlmCredentialSchema>;
/**
 * Body for `POST /api/llm/providers/:provider/test`.
 * When `apiKey` is omitted, the server uses the stored credential (or env
 * fallback). This lets the UI test a key *before* saving it.
 */
export declare const TestLlmCredentialSchema: z.ZodObject<{
    apiKey: z.ZodOptional<z.ZodString>;
}, "strip", z.ZodTypeAny, {
    apiKey?: string | undefined;
}, {
    apiKey?: string | undefined;
}>;
export type TestLlmCredentialRequest = z.infer<typeof TestLlmCredentialSchema>;
export declare const TestLlmCredentialResponseSchema: z.ZodObject<{
    ok: z.ZodLiteral<true>;
    provider: z.ZodEnum<["openai", "anthropic"]>;
    /** Number of models the provider returned during the probe. */
    modelCount: z.ZodNumber;
    latencyMs: z.ZodNumber;
}, "strip", z.ZodTypeAny, {
    ok: true;
    provider: "openai" | "anthropic";
    modelCount: number;
    latencyMs: number;
}, {
    ok: true;
    provider: "openai" | "anthropic";
    modelCount: number;
    latencyMs: number;
}>;
export type TestLlmCredentialResponse = z.infer<typeof TestLlmCredentialResponseSchema>;
export declare const SafetyWarningSchema: z.ZodObject<{
    code: z.ZodEnum<["select_star", "missing_limit", "unknown_table", "unknown_column", "unknown_label", "dml_blocked", "ddl_blocked", "ambiguous_join", "cypher_write_blocked"]>;
    message: z.ZodString;
    severity: z.ZodEnum<["info", "warn", "error"]>;
}, "strip", z.ZodTypeAny, {
    code: "select_star" | "missing_limit" | "unknown_table" | "unknown_column" | "unknown_label" | "dml_blocked" | "ddl_blocked" | "ambiguous_join" | "cypher_write_blocked";
    message: string;
    severity: "info" | "warn" | "error";
}, {
    code: "select_star" | "missing_limit" | "unknown_table" | "unknown_column" | "unknown_label" | "dml_blocked" | "ddl_blocked" | "ambiguous_join" | "cypher_write_blocked";
    message: string;
    severity: "info" | "warn" | "error";
}>;
export type SafetyWarning = z.infer<typeof SafetyWarningSchema>;
export declare const Nl2SqlResponseSchema: z.ZodObject<{
    query: z.ZodString;
    language: z.ZodEnum<["sql", "cypher", "qdrant", "soql"]>;
    dialect: z.ZodEnum<["postgres", "mysql", "mariadb", "mssql", "sqlite", "cockroach", "oracle", "clickhouse", "duckdb", "mongodb", "neo4j", "falkordb", "ultipa", "qdrant", "redis", "elasticsearch", "salesforce", "salesforce-data-cloud"]>;
    explanation: z.ZodString;
    joinNotes: z.ZodArray<z.ZodString, "many">;
    involvedEntities: z.ZodArray<z.ZodString, "many">;
    warnings: z.ZodArray<z.ZodObject<{
        code: z.ZodEnum<["select_star", "missing_limit", "unknown_table", "unknown_column", "unknown_label", "dml_blocked", "ddl_blocked", "ambiguous_join", "cypher_write_blocked"]>;
        message: z.ZodString;
        severity: z.ZodEnum<["info", "warn", "error"]>;
    }, "strip", z.ZodTypeAny, {
        code: "select_star" | "missing_limit" | "unknown_table" | "unknown_column" | "unknown_label" | "dml_blocked" | "ddl_blocked" | "ambiguous_join" | "cypher_write_blocked";
        message: string;
        severity: "info" | "warn" | "error";
    }, {
        code: "select_star" | "missing_limit" | "unknown_table" | "unknown_column" | "unknown_label" | "dml_blocked" | "ddl_blocked" | "ambiguous_join" | "cypher_write_blocked";
        message: string;
        severity: "info" | "warn" | "error";
    }>, "many">;
    retries: z.ZodNumber;
    provider: z.ZodEnum<["ollama", "openai", "anthropic"]>;
    model: z.ZodString;
}, "strip", z.ZodTypeAny, {
    dialect: "postgres" | "mysql" | "mariadb" | "mssql" | "sqlite" | "cockroach" | "oracle" | "clickhouse" | "duckdb" | "neo4j" | "falkordb" | "ultipa" | "mongodb" | "qdrant" | "redis" | "elasticsearch" | "salesforce" | "salesforce-data-cloud";
    query: string;
    language: "qdrant" | "sql" | "cypher" | "soql";
    provider: "ollama" | "openai" | "anthropic";
    model: string;
    explanation: string;
    joinNotes: string[];
    involvedEntities: string[];
    warnings: {
        code: "select_star" | "missing_limit" | "unknown_table" | "unknown_column" | "unknown_label" | "dml_blocked" | "ddl_blocked" | "ambiguous_join" | "cypher_write_blocked";
        message: string;
        severity: "info" | "warn" | "error";
    }[];
    retries: number;
}, {
    dialect: "postgres" | "mysql" | "mariadb" | "mssql" | "sqlite" | "cockroach" | "oracle" | "clickhouse" | "duckdb" | "neo4j" | "falkordb" | "ultipa" | "mongodb" | "qdrant" | "redis" | "elasticsearch" | "salesforce" | "salesforce-data-cloud";
    query: string;
    language: "qdrant" | "sql" | "cypher" | "soql";
    provider: "ollama" | "openai" | "anthropic";
    model: string;
    explanation: string;
    joinNotes: string[];
    involvedEntities: string[];
    warnings: {
        code: "select_star" | "missing_limit" | "unknown_table" | "unknown_column" | "unknown_label" | "dml_blocked" | "ddl_blocked" | "ambiguous_join" | "cypher_write_blocked";
        message: string;
        severity: "info" | "warn" | "error";
    }[];
    retries: number;
}>;
export type Nl2SqlResponse = z.infer<typeof Nl2SqlResponseSchema>;
export declare const ExecuteQueryRequestSchema: z.ZodObject<{
    connectionId: z.ZodString;
    query: z.ZodString;
    rowLimit: z.ZodDefault<z.ZodNumber>;
}, "strip", z.ZodTypeAny, {
    query: string;
    connectionId: string;
    rowLimit: number;
}, {
    query: string;
    connectionId: string;
    rowLimit?: number | undefined;
}>;
export type ExecuteQueryRequest = z.infer<typeof ExecuteQueryRequestSchema>;
export declare const ExecuteQueryResponseSchema: z.ZodObject<{
    columns: z.ZodArray<z.ZodString, "many">;
    rows: z.ZodArray<z.ZodArray<z.ZodUnknown, "many">, "many">;
    rowCount: z.ZodNumber;
    durationMs: z.ZodNumber;
    truncated: z.ZodBoolean;
}, "strip", z.ZodTypeAny, {
    rowCount: number;
    columns: string[];
    rows: unknown[][];
    durationMs: number;
    truncated: boolean;
}, {
    rowCount: number;
    columns: string[];
    rows: unknown[][];
    durationMs: number;
    truncated: boolean;
}>;
export type ExecuteQueryResponse = z.infer<typeof ExecuteQueryResponseSchema>;
export declare const SampleRequestSchema: z.ZodObject<{
    connectionId: z.ZodString;
    tableId: z.ZodString;
    rowLimit: z.ZodDefault<z.ZodNumber>;
}, "strip", z.ZodTypeAny, {
    connectionId: string;
    rowLimit: number;
    tableId: string;
}, {
    connectionId: string;
    tableId: string;
    rowLimit?: number | undefined;
}>;
export type SampleRequest = z.infer<typeof SampleRequestSchema>;
/**
 * "Ask" flow — single-shot pipeline that:
 *   1. Translates the natural-language prompt into a safe query.
 *   2. Executes that query against the connection.
 *   3. Summarizes the resulting rows in plain language.
 *
 * The response always includes the translation. Execution + summary are
 * best-effort: a translated-but-unexecutable query still returns
 * `translation` with `executionError` populated so the UI can surface it
 * without losing the generated query.
 */
export declare const Nl2QueryAskRequestSchema: z.ZodObject<{
    connectionId: z.ZodString;
    prompt: z.ZodString;
    provider: z.ZodDefault<z.ZodEnum<["ollama", "openai", "anthropic"]>>;
    model: z.ZodOptional<z.ZodString>;
    rowLimit: z.ZodDefault<z.ZodNumber>;
    locale: z.ZodDefault<z.ZodEnum<["en", "it"]>>;
    history: z.ZodDefault<z.ZodArray<z.ZodObject<{
        prompt: z.ZodString;
        query: z.ZodOptional<z.ZodString>;
        language: z.ZodOptional<z.ZodEnum<["sql", "cypher", "qdrant", "soql"]>>;
        rowCount: z.ZodOptional<z.ZodNullable<z.ZodNumber>>;
        ok: z.ZodOptional<z.ZodBoolean>;
    }, "strip", z.ZodTypeAny, {
        prompt: string;
        query?: string | undefined;
        language?: "qdrant" | "sql" | "cypher" | "soql" | undefined;
        rowCount?: number | null | undefined;
        ok?: boolean | undefined;
    }, {
        prompt: string;
        query?: string | undefined;
        language?: "qdrant" | "sql" | "cypher" | "soql" | undefined;
        rowCount?: number | null | undefined;
        ok?: boolean | undefined;
    }>, "many">>;
}, "strip", z.ZodTypeAny, {
    prompt: string;
    connectionId: string;
    provider: "ollama" | "openai" | "anthropic";
    rowLimit: number;
    locale: "en" | "it";
    history: {
        prompt: string;
        query?: string | undefined;
        language?: "qdrant" | "sql" | "cypher" | "soql" | undefined;
        rowCount?: number | null | undefined;
        ok?: boolean | undefined;
    }[];
    model?: string | undefined;
}, {
    prompt: string;
    connectionId: string;
    provider?: "ollama" | "openai" | "anthropic" | undefined;
    model?: string | undefined;
    rowLimit?: number | undefined;
    locale?: "en" | "it" | undefined;
    history?: {
        prompt: string;
        query?: string | undefined;
        language?: "qdrant" | "sql" | "cypher" | "soql" | undefined;
        rowCount?: number | null | undefined;
        ok?: boolean | undefined;
    }[] | undefined;
}>;
export type Nl2QueryAskRequest = z.infer<typeof Nl2QueryAskRequestSchema>;
export declare const AskExecutionErrorSchema: z.ZodObject<{
    code: z.ZodString;
    message: z.ZodString;
}, "strip", z.ZodTypeAny, {
    code: string;
    message: string;
}, {
    code: string;
    message: string;
}>;
export type AskExecutionError = z.infer<typeof AskExecutionErrorSchema>;
export declare const Nl2QueryAskResponseSchema: z.ZodObject<{
    translation: z.ZodObject<{
        query: z.ZodString;
        language: z.ZodEnum<["sql", "cypher", "qdrant", "soql"]>;
        dialect: z.ZodEnum<["postgres", "mysql", "mariadb", "mssql", "sqlite", "cockroach", "oracle", "clickhouse", "duckdb", "mongodb", "neo4j", "falkordb", "ultipa", "qdrant", "redis", "elasticsearch", "salesforce", "salesforce-data-cloud"]>;
        explanation: z.ZodString;
        joinNotes: z.ZodArray<z.ZodString, "many">;
        involvedEntities: z.ZodArray<z.ZodString, "many">;
        warnings: z.ZodArray<z.ZodObject<{
            code: z.ZodEnum<["select_star", "missing_limit", "unknown_table", "unknown_column", "unknown_label", "dml_blocked", "ddl_blocked", "ambiguous_join", "cypher_write_blocked"]>;
            message: z.ZodString;
            severity: z.ZodEnum<["info", "warn", "error"]>;
        }, "strip", z.ZodTypeAny, {
            code: "select_star" | "missing_limit" | "unknown_table" | "unknown_column" | "unknown_label" | "dml_blocked" | "ddl_blocked" | "ambiguous_join" | "cypher_write_blocked";
            message: string;
            severity: "info" | "warn" | "error";
        }, {
            code: "select_star" | "missing_limit" | "unknown_table" | "unknown_column" | "unknown_label" | "dml_blocked" | "ddl_blocked" | "ambiguous_join" | "cypher_write_blocked";
            message: string;
            severity: "info" | "warn" | "error";
        }>, "many">;
        retries: z.ZodNumber;
        provider: z.ZodEnum<["ollama", "openai", "anthropic"]>;
        model: z.ZodString;
    }, "strip", z.ZodTypeAny, {
        dialect: "postgres" | "mysql" | "mariadb" | "mssql" | "sqlite" | "cockroach" | "oracle" | "clickhouse" | "duckdb" | "neo4j" | "falkordb" | "ultipa" | "mongodb" | "qdrant" | "redis" | "elasticsearch" | "salesforce" | "salesforce-data-cloud";
        query: string;
        language: "qdrant" | "sql" | "cypher" | "soql";
        provider: "ollama" | "openai" | "anthropic";
        model: string;
        explanation: string;
        joinNotes: string[];
        involvedEntities: string[];
        warnings: {
            code: "select_star" | "missing_limit" | "unknown_table" | "unknown_column" | "unknown_label" | "dml_blocked" | "ddl_blocked" | "ambiguous_join" | "cypher_write_blocked";
            message: string;
            severity: "info" | "warn" | "error";
        }[];
        retries: number;
    }, {
        dialect: "postgres" | "mysql" | "mariadb" | "mssql" | "sqlite" | "cockroach" | "oracle" | "clickhouse" | "duckdb" | "neo4j" | "falkordb" | "ultipa" | "mongodb" | "qdrant" | "redis" | "elasticsearch" | "salesforce" | "salesforce-data-cloud";
        query: string;
        language: "qdrant" | "sql" | "cypher" | "soql";
        provider: "ollama" | "openai" | "anthropic";
        model: string;
        explanation: string;
        joinNotes: string[];
        involvedEntities: string[];
        warnings: {
            code: "select_star" | "missing_limit" | "unknown_table" | "unknown_column" | "unknown_label" | "dml_blocked" | "ddl_blocked" | "ambiguous_join" | "cypher_write_blocked";
            message: string;
            severity: "info" | "warn" | "error";
        }[];
        retries: number;
    }>;
    result: z.ZodNullable<z.ZodObject<{
        columns: z.ZodArray<z.ZodString, "many">;
        rows: z.ZodArray<z.ZodArray<z.ZodUnknown, "many">, "many">;
        rowCount: z.ZodNumber;
        durationMs: z.ZodNumber;
        truncated: z.ZodBoolean;
    }, "strip", z.ZodTypeAny, {
        rowCount: number;
        columns: string[];
        rows: unknown[][];
        durationMs: number;
        truncated: boolean;
    }, {
        rowCount: number;
        columns: string[];
        rows: unknown[][];
        durationMs: number;
        truncated: boolean;
    }>>;
    executionError: z.ZodNullable<z.ZodObject<{
        code: z.ZodString;
        message: z.ZodString;
    }, "strip", z.ZodTypeAny, {
        code: string;
        message: string;
    }, {
        code: string;
        message: string;
    }>>;
    /** One- to three-sentence headline answer in the user's locale. */
    summary: z.ZodString;
    /**
     * Optional bullets that pull concrete values from the rows ("Acme: $1.2M",
     * "TopCo: $980k"). Rendered in the chat bubble below the summary so the
     * conversation reads as a natural, data-grounded reply rather than just
     * "see the table below".
     */
    highlights: z.ZodDefault<z.ZodArray<z.ZodString, "many">>;
    /**
     * Suggested follow-up questions the user might ask next (locale-aware).
     * Rendered as clickable chips that immediately fire a new turn.
     */
    followUps: z.ZodDefault<z.ZodArray<z.ZodString, "many">>;
    totalDurationMs: z.ZodNumber;
}, "strip", z.ZodTypeAny, {
    translation: {
        dialect: "postgres" | "mysql" | "mariadb" | "mssql" | "sqlite" | "cockroach" | "oracle" | "clickhouse" | "duckdb" | "neo4j" | "falkordb" | "ultipa" | "mongodb" | "qdrant" | "redis" | "elasticsearch" | "salesforce" | "salesforce-data-cloud";
        query: string;
        language: "qdrant" | "sql" | "cypher" | "soql";
        provider: "ollama" | "openai" | "anthropic";
        model: string;
        explanation: string;
        joinNotes: string[];
        involvedEntities: string[];
        warnings: {
            code: "select_star" | "missing_limit" | "unknown_table" | "unknown_column" | "unknown_label" | "dml_blocked" | "ddl_blocked" | "ambiguous_join" | "cypher_write_blocked";
            message: string;
            severity: "info" | "warn" | "error";
        }[];
        retries: number;
    };
    result: {
        rowCount: number;
        columns: string[];
        rows: unknown[][];
        durationMs: number;
        truncated: boolean;
    } | null;
    executionError: {
        code: string;
        message: string;
    } | null;
    summary: string;
    highlights: string[];
    followUps: string[];
    totalDurationMs: number;
}, {
    translation: {
        dialect: "postgres" | "mysql" | "mariadb" | "mssql" | "sqlite" | "cockroach" | "oracle" | "clickhouse" | "duckdb" | "neo4j" | "falkordb" | "ultipa" | "mongodb" | "qdrant" | "redis" | "elasticsearch" | "salesforce" | "salesforce-data-cloud";
        query: string;
        language: "qdrant" | "sql" | "cypher" | "soql";
        provider: "ollama" | "openai" | "anthropic";
        model: string;
        explanation: string;
        joinNotes: string[];
        involvedEntities: string[];
        warnings: {
            code: "select_star" | "missing_limit" | "unknown_table" | "unknown_column" | "unknown_label" | "dml_blocked" | "ddl_blocked" | "ambiguous_join" | "cypher_write_blocked";
            message: string;
            severity: "info" | "warn" | "error";
        }[];
        retries: number;
    };
    result: {
        rowCount: number;
        columns: string[];
        rows: unknown[][];
        durationMs: number;
        truncated: boolean;
    } | null;
    executionError: {
        code: string;
        message: string;
    } | null;
    summary: string;
    totalDurationMs: number;
    highlights?: string[] | undefined;
    followUps?: string[] | undefined;
}>;
export type Nl2QueryAskResponse = z.infer<typeof Nl2QueryAskResponseSchema>;
//# sourceMappingURL=nl2sql.d.ts.map