export interface RedisCommandToken {
    command: string;
    args: string[];
}
export interface ValidateCommandResult {
    parsed: RedisCommandToken;
    warnings: string[];
}
/**
 * Parse a single Redis command line. Accepts space-separated args with
 * optional double-quoted strings for values containing spaces.
 * Rejects multi-statement input (newlines or semicolons).
 */
export declare function parseRedisCommand(input: string): RedisCommandToken;
/**
 * Validate a Redis command against the read-only whitelist.
 * Throws with `code: 'unsafe_redis_command'` style message on violation.
 */
export declare function validateRedisCommand(input: string): ValidateCommandResult;
export declare function isReadCommand(cmd: string): boolean;
//# sourceMappingURL=safety.d.ts.map