import { Injectable, Logger } from '@nestjs/common';
import { LlmProviderError, type RemoteLlmProvider, type RemoteModel } from '@dbview/shared';

const FETCH_TIMEOUT_MS = 10_000;
const ANTHROPIC_VERSION = '2023-06-01';

/**
 * Talks directly to the provider's REST API to:
 *   - list available models (so the UI can filter to models the caller's
 *     account can actually invoke, rather than a hard-coded allowlist that
 *     ages out as providers release new models)
 *   - validate an API key in a single round-trip
 *
 * We intentionally use the raw REST endpoints rather than going through the
 * `ai` SDK: the SDK is shaped around generation, not metadata listing, and
 * the model-list endpoints are stable and trivial to hit directly.
 */
@Injectable()
export class RemoteProviderService {
  private readonly logger = new Logger('RemoteProviderService');

  async listModels(provider: RemoteLlmProvider, apiKey: string): Promise<RemoteModel[]> {
    if (provider === 'openai') return this.listOpenAi(apiKey);
    return this.listAnthropic(apiKey);
  }

  /**
   * Probe the provider with the supplied key. Reuses the model-list endpoint
   * because it is the cheapest authenticated GET available on both providers
   * (no token cost, no usage quota impact).
   */
  async test(
    provider: RemoteLlmProvider,
    apiKey: string
  ): Promise<{ modelCount: number; latencyMs: number }> {
    const t0 = Date.now();
    const models = await this.listModels(provider, apiKey);
    return { modelCount: models.length, latencyMs: Date.now() - t0 };
  }

  private async listOpenAi(apiKey: string): Promise<RemoteModel[]> {
    const payload = await this.fetchJson(
      'https://api.openai.com/v1/models',
      { headers: { Authorization: `Bearer ${apiKey}` } },
      'openai'
    );
    const raw = ((payload as { data?: OpenAiModel[] }).data ?? []) as OpenAiModel[];
    return raw
      .filter((m) => typeof m.id === 'string' && m.id.length > 0)
      .map(
        (m): RemoteModel => ({
          id: m.id,
          displayName: m.id,
          family: deriveOpenAiFamily(m.id),
          createdAt:
            typeof m.created === 'number' ? new Date(m.created * 1000).toISOString() : undefined,
        })
      );
  }

  private async listAnthropic(apiKey: string): Promise<RemoteModel[]> {
    const payload = await this.fetchJson(
      'https://api.anthropic.com/v1/models?limit=1000',
      {
        headers: {
          'x-api-key': apiKey,
          'anthropic-version': ANTHROPIC_VERSION,
        },
      },
      'anthropic'
    );
    const raw = ((payload as { data?: AnthropicModel[] }).data ?? []) as AnthropicModel[];
    return raw
      .filter((m) => typeof m.id === 'string' && m.id.length > 0)
      .map(
        (m): RemoteModel => ({
          id: m.id,
          displayName: m.display_name ?? m.id,
          family: deriveAnthropicFamily(m.id),
          createdAt: typeof m.created_at === 'string' ? m.created_at : undefined,
        })
      );
  }

  private async fetchJson(
    url: string,
    init: RequestInit,
    provider: RemoteLlmProvider
  ): Promise<unknown> {
    const ctrl = new AbortController();
    const timer = setTimeout(() => ctrl.abort(), FETCH_TIMEOUT_MS);
    try {
      const res = await fetch(url, {
        ...init,
        method: 'GET',
        signal: ctrl.signal,
        headers: { ...init.headers, Accept: 'application/json' },
      });
      if (!res.ok) {
        const body = await safeReadText(res);
        const reason = extractProviderError(body) ?? `${res.status} ${res.statusText}`;
        // Don't leak the upstream URL — it is constant and not interesting.
        throw new LlmProviderError(`${provider}: ${reason}`);
      }
      return (await res.json()) as unknown;
    } catch (err) {
      if (err instanceof LlmProviderError) throw err;
      if ((err as Error).name === 'AbortError') {
        throw new LlmProviderError(`${provider}: request timed out after ${FETCH_TIMEOUT_MS}ms.`);
      }
      throw new LlmProviderError(`${provider}: ${(err as Error).message}`);
    } finally {
      clearTimeout(timer);
    }
  }
}

interface OpenAiModel {
  id: string;
  object?: string;
  created?: number;
  owned_by?: string;
}

interface AnthropicModel {
  id: string;
  type?: string;
  display_name?: string;
  created_at?: string;
}

async function safeReadText(res: Response): Promise<string> {
  try {
    return await res.text();
  } catch {
    return '';
  }
}

/**
 * Provider errors are JSON envelopes that share a `message` somewhere in the
 * payload. We pull it out best-effort and fall back to the raw body so the
 * UI can show *something* actionable rather than an opaque HTTP status code.
 */
function extractProviderError(body: string): string | undefined {
  if (!body) return undefined;
  try {
    const parsed = JSON.parse(body) as {
      error?: { message?: string; type?: string };
      message?: string;
    };
    return parsed.error?.message ?? parsed.message ?? body.slice(0, 240);
  } catch {
    return body.slice(0, 240);
  }
}

function deriveOpenAiFamily(id: string): string {
  // gpt-4o-mini → gpt-4o ; o1-mini → o1 ; text-embedding-3-small → text-embedding-3
  const lower = id.toLowerCase();
  if (lower.startsWith('gpt-4o')) return 'gpt-4o';
  if (lower.startsWith('gpt-4')) return 'gpt-4';
  if (lower.startsWith('gpt-3.5')) return 'gpt-3.5';
  if (lower.startsWith('o1')) return 'o1';
  if (lower.startsWith('o3')) return 'o3';
  if (lower.startsWith('text-embedding')) return 'embeddings';
  if (lower.startsWith('whisper') || lower.startsWith('tts')) return 'audio';
  if (lower.startsWith('dall-e')) return 'image';
  return id.split('-')[0] ?? id;
}

function deriveAnthropicFamily(id: string): string {
  // claude-opus-4-5-20251015 → claude-opus ; claude-3-5-sonnet → claude-3.5
  const lower = id.toLowerCase();
  if (lower.includes('opus')) return 'claude-opus';
  if (lower.includes('sonnet')) return 'claude-sonnet';
  if (lower.includes('haiku')) return 'claude-haiku';
  return 'claude';
}
