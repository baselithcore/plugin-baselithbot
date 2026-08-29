export class DbviewError extends Error {
    code;
    status;
    constructor(message, code, status = 400) {
        super(message);
        this.code = code;
        this.status = status;
        this.name = 'DbviewError';
    }
}
export class UnsafeSqlError extends DbviewError {
    constructor(message) {
        super(message, 'unsafe_sql', 422);
    }
}
export class IntrospectionError extends DbviewError {
    constructor(message) {
        super(message, 'introspection_failed', 502);
    }
}
/**
 * Raised when a database is reachable on the network layer but introspection
 * cannot complete (permission denied, missing tables, etc) AND we have no
 * cached schema. Distinct from generic IntrospectionError so UIs can offer
 * "fix permissions" guidance instead of "retry connection".
 */
export class ConnectionUnreachableError extends DbviewError {
    details;
    constructor(message, details) {
        super(message, 'connection_unreachable', 503);
        this.details = details;
    }
}
export class LlmProviderError extends DbviewError {
    constructor(message) {
        super(message, 'llm_provider_error', 502);
    }
}
/**
 * Raised when a query exceeds its execution deadline (engine-side
 * statement timeout or driver-level gRPC deadline). Distinct from
 * IntrospectionError / LlmProviderError: query reached the engine but
 * did not finish in time. UI can offer "narrow filter" guidance.
 */
export class QueryTimeoutError extends DbviewError {
    details;
    constructor(message, details = {}) {
        super(message, 'query_timeout', 504);
        this.details = details;
    }
}
export class UnauthorizedError extends DbviewError {
    constructor(message = 'Authentication required.') {
        super(message, 'unauthorized', 401);
    }
}
export class ForbiddenError extends DbviewError {
    constructor(message = 'Insufficient privileges.') {
        super(message, 'forbidden', 403);
    }
}
export class InvalidCredentialsError extends DbviewError {
    constructor() {
        super('Invalid email or password.', 'invalid_credentials', 401);
    }
}
export class TokenReplayError extends DbviewError {
    constructor() {
        super('Refresh token replay detected. Session revoked.', 'token_replay', 401);
    }
}
/**
 * Raised when the model's raw output is structurally unusable (no SQL
 * keyword found, prose-only response, etc). Retryable — the service
 * can bump the temperature and try again. Distinct from LlmProviderError
 * (network/HTTP failures, which are NOT retryable in the same loop).
 */
export class ModelOutputError extends DbviewError {
    constructor(message) {
        super(message, 'model_output_invalid', 422);
    }
}
/**
 * Raised when the model could not produce a query referencing only
 * the entities present in the schema, even after retries. Distinct from
 * generic provider error: this is a grounding failure (model hallucination
 * or unanswerable question), not a transient LLM/connectivity issue.
 */
export class SchemaMismatchError extends DbviewError {
    details;
    constructor(message, details) {
        super(message, 'schema_mismatch', 422);
        this.details = details;
    }
}
//# sourceMappingURL=errors.js.map