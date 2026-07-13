import { LlmProviderSchema } from '@dbview/shared';
import type {
  GovernanceContext,
  GovernedScope,
} from '../common/request-context.js';

/**
 * Parse the live LLM-governance headers the BaselithCore proxy mints per
 * request (see `plugins/dbview/llm_governance.py::governed_request_headers`).
 *
 * The proxy strips any inbound copy of these before forwarding, so their
 * presence is trusted. Returns `undefined` when none are set (unpinned or the
 * request did not come through the governing proxy) — callers then fall back
 * to the spawn-time `DBVIEW_LLM_ENFORCED_*` env.
 */
type RawHeaders = Record<string, string | string[] | undefined>;

function readHeader(headers: RawHeaders, name: string): string | undefined {
  const value = headers[name];
  const single = Array.isArray(value) ? value[0] : value;
  return single && single.length > 0 ? single : undefined;
}

function readScope(
  headers: RawHeaders,
  providerHeader: string,
  modelHeader: string
): GovernedScope | undefined {
  const raw = readHeader(headers, providerHeader);
  if (!raw) return undefined;
  const parsed = LlmProviderSchema.safeParse(raw);
  if (!parsed.success) return undefined;
  return { provider: parsed.data, model: readHeader(headers, modelHeader) };
}

export function parseGovernanceHeaders(
  headers: RawHeaders
): GovernanceContext | undefined {
  const translate = readScope(
    headers,
    'x-dbview-gov-nl2sql-provider',
    'x-dbview-gov-nl2sql-model'
  );
  const explain = readScope(
    headers,
    'x-dbview-gov-explain-provider',
    'x-dbview-gov-explain-model'
  );
  const openaiKey = readHeader(headers, 'x-dbview-gov-openai-key');
  const anthropicKey = readHeader(headers, 'x-dbview-gov-anthropic-key');
  const ollamaBase = readHeader(headers, 'x-dbview-gov-ollama-base');
  if (!translate && !explain && !openaiKey && !anthropicKey && !ollamaBase) {
    return undefined;
  }
  return { translate, explain, openaiKey, anthropicKey, ollamaBase };
}
