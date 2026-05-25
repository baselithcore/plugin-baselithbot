import { Injectable } from '@nestjs/common';
import { LlmProviderError, type OllamaModel } from '@dbview/shared';

@Injectable()
export class OllamaService {
  /** Default base URL when none provided. Mirrors LLM adapter default. */
  defaultBaseUrl(): string {
    return process.env.OLLAMA_BASE_URL ?? 'http://localhost:11434/api';
  }

  /**
   * Fetch installed models from the Ollama instance configured via env.
   * The endpoint is intentionally not overridable per request — it is a
   * deployment-level setting (OLLAMA_BASE_URL).
   */
  async listModels(): Promise<{ baseUrl: string; models: OllamaModel[] }> {
    const url = normalizeBase(this.defaultBaseUrl());
    const tagsUrl = `${url}/tags`;
    const ctrl = new AbortController();
    const timeout = setTimeout(() => ctrl.abort(), 5_000);
    try {
      const res = await fetch(tagsUrl, { signal: ctrl.signal });
      if (!res.ok) {
        throw new LlmProviderError(`Ollama ${tagsUrl} returned ${res.status} ${res.statusText}.`);
      }
      const json = (await res.json()) as { models?: RawModel[] };
      const models = (json.models ?? []).map(toModel);
      return { baseUrl: url, models };
    } catch (err) {
      if (err instanceof LlmProviderError) throw err;
      throw new LlmProviderError(`Cannot reach Ollama at ${tagsUrl}: ${(err as Error).message}`);
    } finally {
      clearTimeout(timeout);
    }
  }
}

interface RawModel {
  name: string;
  size?: number;
  digest?: string;
  modified_at?: string;
  details?: { family?: string; parameter_size?: string };
}

function toModel(r: RawModel): OllamaModel {
  return {
    name: r.name,
    size: r.size,
    digest: r.digest,
    modifiedAt: r.modified_at,
    family: r.details?.family,
    parameterSize: r.details?.parameter_size,
  };
}

function normalizeBase(raw: string): string {
  let s = raw.trim().replace(/\/+$/, '');
  if (!/\/api$/.test(s)) s = `${s}/api`;
  return s;
}
