export declare class DbviewError extends Error {
    readonly code: string;
    readonly status: number;
    constructor(message: string, code: string, status?: number);
}
export declare class UnsafeSqlError extends DbviewError {
    constructor(message: string);
}
export declare class IntrospectionError extends DbviewError {
    constructor(message: string);
}
/**
 * Raised when a database is reachable on the network layer but introspection
 * cannot complete (permission denied, missing tables, etc) AND we have no
 * cached schema. Distinct from generic IntrospectionError so UIs can offer
 * "fix permissions" guidance instead of "retry connection".
 */
export declare class ConnectionUnreachableError extends DbviewError {
    readonly details: {
        cause: 'refused' | 'timeout' | 'dns' | 'tls' | 'auth' | 'unknown';
        host?: string;
        port?: number;
    };
    constructor(message: string, details: {
        cause: 'refused' | 'timeout' | 'dns' | 'tls' | 'auth' | 'unknown';
        host?: string;
        port?: number;
    });
}
export declare class LlmProviderError extends DbviewError {
    constructor(message: string);
}
/**
 * Raised when a query exceeds its execution deadline (engine-side
 * statement timeout or driver-level gRPC deadline). Distinct from
 * IntrospectionError / LlmProviderError: query reached the engine but
 * did not finish in time. UI can offer "narrow filter" guidance.
 */
export declare class QueryTimeoutError extends DbviewError {
    readonly details: {
        dialect?: string;
        timeoutMs?: number;
    };
    constructor(message: string, details?: {
        dialect?: string;
        timeoutMs?: number;
    });
}
export declare class UnauthorizedError extends DbviewError {
    constructor(message?: string);
}
export declare class ForbiddenError extends DbviewError {
    constructor(message?: string);
}
export declare class InvalidCredentialsError extends DbviewError {
    constructor();
}
export declare class TokenReplayError extends DbviewError {
    constructor();
}
/**
 * Raised when the model's raw output is structurally unusable (no SQL
 * keyword found, prose-only response, etc). Retryable — the service
 * can bump the temperature and try again. Distinct from LlmProviderError
 * (network/HTTP failures, which are NOT retryable in the same loop).
 */
export declare class ModelOutputError extends DbviewError {
    constructor(message: string);
}
export interface SchemaMismatchDetails {
    attempts: number;
    unknownEntities: string[];
    availableEntities: string[];
    suggestions: Record<string, string[]>;
    /** Last rejected SQL/SOQL the model produced. Useful for UI debug + manual fix. */
    lastRejectedQuery?: string;
    /**
     * For each unknown column, the list of real tables that actually contain a
     * column with that bare name. Empty for table/sObject errors.
     */
    columnLocations?: Record<string, string[]>;
}
/**
 * Raised when the model could not produce a query referencing only
 * the entities present in the schema, even after retries. Distinct from
 * generic provider error: this is a grounding failure (model hallucination
 * or unanswerable question), not a transient LLM/connectivity issue.
 */
export declare class SchemaMismatchError extends DbviewError {
    readonly details: SchemaMismatchDetails;
    constructor(message: string, details: SchemaMismatchDetails);
}
//# sourceMappingURL=errors.d.ts.map