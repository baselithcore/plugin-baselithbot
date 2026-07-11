import {
  BadRequestException,
  Body,
  Controller,
  Delete,
  Get,
  Param,
  Post,
  Put,
} from '@nestjs/common';
import {
  RemoteLlmProviderSchema,
  SetLlmCredentialSchema,
  TestLlmCredentialSchema,
  type LlmCredentialStatus,
  type LlmGovernanceState,
  type OllamaModelsResponse,
  type RemoteLlmProvider,
  type RemoteModelsResponse,
  type TestLlmCredentialResponse,
} from '@dbview/shared';
import { ZodPipe } from '../common/zod.pipe.js';
import { CurrentUser } from '../auth/decorators.js';
import type { AuthPrincipal } from '../auth/auth.types.js';
import { OllamaService } from './ollama.service.js';
import { LlmCredentialsService } from './credentials.service.js';
import { RemoteProviderService } from './remote-provider.service.js';
import { LlmGovernanceService } from './governance.service.js';

@Controller('llm')
export class LlmController {
  constructor(
    private readonly ollama: OllamaService,
    private readonly credentials: LlmCredentialsService,
    private readonly remote: RemoteProviderService,
    private readonly governance: LlmGovernanceService
  ) {}

  /**
   * Central LLM-governance state. When a scope is enforced (operator pinned
   * the provider from the auth console), the SPA hides the matching per-user
   * LLM controls — the pin already wins server-side regardless.
   */
  @Get('governance')
  governanceState(): LlmGovernanceState {
    return this.governance.state();
  }

  @Get('ollama/models')
  async listOllama(): Promise<OllamaModelsResponse> {
    return this.ollama.listModels();
  }

  @Get('providers/:provider/credential')
  getCredential(
    @Param('provider') providerRaw: string,
    @CurrentUser() principal: AuthPrincipal
  ): LlmCredentialStatus {
    const provider = parseProvider(providerRaw);
    return this.credentials.status(provider, principal);
  }

  @Put('providers/:provider/credential')
  setCredential(
    @Param('provider') providerRaw: string,
    @Body(new ZodPipe(SetLlmCredentialSchema)) body: { apiKey: string },
    @CurrentUser() principal: AuthPrincipal
  ): LlmCredentialStatus {
    const provider = parseProvider(providerRaw);
    return this.credentials.upsert(provider, body.apiKey, principal);
  }

  @Delete('providers/:provider/credential')
  deleteCredential(
    @Param('provider') providerRaw: string,
    @CurrentUser() principal: AuthPrincipal
  ): LlmCredentialStatus {
    const provider = parseProvider(providerRaw);
    return this.credentials.remove(provider, principal);
  }

  /**
   * Validate a provider key.
   *
   * The body's `apiKey` (when supplied) takes precedence over any stored
   * credential — this lets the UI test a fresh key before persisting it, so
   * users get immediate feedback ("invalid key") without first overwriting
   * a known-good stored value with a typo.
   */
  @Post('providers/:provider/test')
  async testCredential(
    @Param('provider') providerRaw: string,
    @Body(new ZodPipe(TestLlmCredentialSchema)) body: { apiKey?: string },
    @CurrentUser() principal: AuthPrincipal
  ): Promise<TestLlmCredentialResponse> {
    const provider = parseProvider(providerRaw);
    const apiKey = body.apiKey ?? this.credentials.resolveApiKey(provider, principal);
    if (!apiKey) {
      throw new BadRequestException({
        code: 'missing_api_key',
        message: `No API key available for ${provider}. Provide one in the request body or save it first.`,
      });
    }
    const probe = await this.remote.test(provider, apiKey);
    return { ok: true, provider, ...probe };
  }

  /**
   * List models the calling user's key has access to. Falls back to env key
   * for service-to-service callers. Errors propagate so the UI can surface
   * "invalid key" / "rate limited" / "network" distinctly.
   */
  @Get('providers/:provider/models')
  async listRemoteModels(
    @Param('provider') providerRaw: string,
    @CurrentUser() principal: AuthPrincipal
  ): Promise<RemoteModelsResponse> {
    const provider = parseProvider(providerRaw);
    const stored = this.credentials.status(provider, principal);
    const apiKey = this.credentials.resolveApiKey(provider, principal);
    if (!apiKey) {
      throw new BadRequestException({
        code: 'missing_api_key',
        message: `No API key configured for ${provider}.`,
      });
    }
    const models = await this.remote.listModels(provider, apiKey);
    return { provider, models, source: stored.envFallback ? 'env' : 'stored' };
  }
}

function parseProvider(raw: string): RemoteLlmProvider {
  const parsed = RemoteLlmProviderSchema.safeParse(raw);
  if (!parsed.success) {
    throw new BadRequestException({
      code: 'unsupported_provider',
      message: `Unsupported provider '${raw}'. Expected one of: openai, anthropic.`,
    });
  }
  return parsed.data;
}
