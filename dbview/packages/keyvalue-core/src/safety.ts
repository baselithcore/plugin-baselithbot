/**
 * Redis read-only command whitelist. Anything outside this set is rejected.
 * See https://redis.io/docs/latest/commands/ for full list.
 */
const READ_COMMANDS = new Set<string>([
  // strings
  'GET',
  'GETRANGE',
  'GETDEL',
  'MGET',
  'STRLEN',
  // generic
  'EXISTS',
  'TYPE',
  'TTL',
  'PTTL',
  'EXPIRETIME',
  'PEXPIRETIME',
  'OBJECT',
  'KEYS',
  'SCAN',
  'RANDOMKEY',
  'DBSIZE',
  'INFO',
  'PING',
  'ECHO',
  'CLIENT',
  'MEMORY',
  // hashes
  'HGET',
  'HMGET',
  'HGETALL',
  'HKEYS',
  'HVALS',
  'HLEN',
  'HEXISTS',
  'HSTRLEN',
  'HSCAN',
  'HRANDFIELD',
  // lists
  'LRANGE',
  'LLEN',
  'LINDEX',
  'LPOS',
  // sets
  'SMEMBERS',
  'SCARD',
  'SISMEMBER',
  'SMISMEMBER',
  'SINTER',
  'SUNION',
  'SDIFF',
  'SSCAN',
  'SRANDMEMBER',
  // sorted sets
  'ZRANGE',
  'ZREVRANGE',
  'ZRANGEBYSCORE',
  'ZREVRANGEBYSCORE',
  'ZRANGEBYLEX',
  'ZSCORE',
  'ZCARD',
  'ZCOUNT',
  'ZLEXCOUNT',
  'ZRANK',
  'ZREVRANK',
  'ZSCAN',
  'ZMSCORE',
  // streams
  'XLEN',
  'XRANGE',
  'XREVRANGE',
  'XINFO',
  'XREAD',
  // geo
  'GEOPOS',
  'GEODIST',
  'GEOSEARCH',
  'GEOHASH',
  // bitmap
  'BITCOUNT',
  'BITPOS',
  'GETBIT',
  // hyperloglog
  'PFCOUNT',
  // server
  'CONFIG',
  'COMMAND',
  'TIME',
]);

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
export function parseRedisCommand(input: string): RedisCommandToken {
  const trimmed = input.trim();
  if (!trimmed) throw new Error('Empty command');
  if (/[;\n\r]/.test(trimmed)) {
    throw new Error('Multi-command input not allowed; pass a single command.');
  }
  const tokens: string[] = [];
  let buf = '';
  let inQuote: '"' | "'" | null = null;
  let escaped = false;
  for (const ch of trimmed) {
    if (escaped) {
      buf += ch;
      escaped = false;
      continue;
    }
    if (ch === '\\' && inQuote) {
      escaped = true;
      continue;
    }
    if (inQuote) {
      if (ch === inQuote) {
        inQuote = null;
      } else {
        buf += ch;
      }
      continue;
    }
    if (ch === '"' || ch === "'") {
      inQuote = ch;
      continue;
    }
    if (/\s/.test(ch)) {
      if (buf) {
        tokens.push(buf);
        buf = '';
      }
      continue;
    }
    buf += ch;
  }
  if (inQuote) throw new Error('Unterminated quoted string.');
  if (buf) tokens.push(buf);
  if (tokens.length === 0) throw new Error('Empty command');
  return { command: tokens[0]!.toUpperCase(), args: tokens.slice(1) };
}

/**
 * Validate a Redis command against the read-only whitelist.
 * Throws with `code: 'unsafe_redis_command'` style message on violation.
 */
export function validateRedisCommand(input: string): ValidateCommandResult {
  const parsed = parseRedisCommand(input);
  const warnings: string[] = [];
  if (!READ_COMMANDS.has(parsed.command)) {
    throw new Error(
      `Command '${parsed.command}' is not allowed. dbview only permits read-only Redis commands.`
    );
  }
  if (parsed.command === 'KEYS') {
    warnings.push(
      'KEYS scans the entire keyspace and blocks Redis. Prefer SCAN with COUNT for production data.'
    );
  }
  if (parsed.command === 'CONFIG' && parsed.args[0]?.toUpperCase() !== 'GET') {
    throw new Error("Only 'CONFIG GET <pattern>' is allowed.");
  }
  if (
    parsed.command === 'CLIENT' &&
    !['LIST', 'INFO', 'GETNAME', 'ID'].includes(parsed.args[0]?.toUpperCase() ?? '')
  ) {
    throw new Error("Only 'CLIENT LIST/INFO/GETNAME/ID' subcommands are allowed.");
  }
  return { parsed, warnings };
}

export function isReadCommand(cmd: string): boolean {
  return READ_COMMANDS.has(cmd.toUpperCase());
}
