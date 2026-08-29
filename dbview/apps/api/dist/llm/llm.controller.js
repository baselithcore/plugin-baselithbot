var __decorate = (this && this.__decorate) || function (decorators, target, key, desc) {
    var c = arguments.length, r = c < 3 ? target : desc === null ? desc = Object.getOwnPropertyDescriptor(target, key) : desc, d;
    if (typeof Reflect === "object" && typeof Reflect.decorate === "function") r = Reflect.decorate(decorators, target, key, desc);
    else for (var i = decorators.length - 1; i >= 0; i--) if (d = decorators[i]) r = (c < 3 ? d(r) : c > 3 ? d(target, key, r) : d(target, key)) || r;
    return c > 3 && r && Object.defineProperty(target, key, r), r;
};
var __metadata = (this && this.__metadata) || function (k, v) {
    if (typeof Reflect === "object" && typeof Reflect.metadata === "function") return Reflect.metadata(k, v);
};
var __param = (this && this.__param) || function (paramIndex, decorator) {
    return function (target, key) { decorator(target, key, paramIndex); }
};
import { BadRequestException, Body, Controller, Delete, Get, Param, Post, Put, } from '@nestjs/common';
import { RemoteLlmProviderSchema, SetLlmCredentialSchema, TestLlmCredentialSchema, } from '@dbview/shared';
import { ZodPipe } from '../common/zod.pipe.js';
import { CurrentUser } from '../auth/decorators.js';
import { OllamaService } from './ollama.service.js';
import { LlmCredentialsService } from './credentials.service.js';
import { RemoteProviderService } from './remote-provider.service.js';
import { LlmGovernanceService } from './governance.service.js';
let LlmController = class LlmController {
    ollama;
    credentials;
    remote;
    governance;
    constructor(ollama, credentials, remote, governance) {
        this.ollama = ollama;
        this.credentials = credentials;
        this.remote = remote;
        this.governance = governance;
    }
    /**
     * Central LLM-governance state. When a scope is enforced (operator pinned
     * the provider from the auth console), the SPA hides the matching per-user
     * LLM controls — the pin already wins server-side regardless.
     */
    governanceState() {
        return this.governance.state();
    }
    async listOllama() {
        return this.ollama.listModels();
    }
    getCredential(providerRaw, principal) {
        const provider = parseProvider(providerRaw);
        return this.credentials.status(provider, principal);
    }
    setCredential(providerRaw, body, principal) {
        const provider = parseProvider(providerRaw);
        return this.credentials.upsert(provider, body.apiKey, principal);
    }
    deleteCredential(providerRaw, principal) {
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
    async testCredential(providerRaw, body, principal) {
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
    async listRemoteModels(providerRaw, principal) {
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
};
__decorate([
    Get('governance'),
    __metadata("design:type", Function),
    __metadata("design:paramtypes", []),
    __metadata("design:returntype", Object)
], LlmController.prototype, "governanceState", null);
__decorate([
    Get('ollama/models'),
    __metadata("design:type", Function),
    __metadata("design:paramtypes", []),
    __metadata("design:returntype", Promise)
], LlmController.prototype, "listOllama", null);
__decorate([
    Get('providers/:provider/credential'),
    __param(0, Param('provider')),
    __param(1, CurrentUser()),
    __metadata("design:type", Function),
    __metadata("design:paramtypes", [String, Object]),
    __metadata("design:returntype", Object)
], LlmController.prototype, "getCredential", null);
__decorate([
    Put('providers/:provider/credential'),
    __param(0, Param('provider')),
    __param(1, Body(new ZodPipe(SetLlmCredentialSchema))),
    __param(2, CurrentUser()),
    __metadata("design:type", Function),
    __metadata("design:paramtypes", [String, Object, Object]),
    __metadata("design:returntype", Object)
], LlmController.prototype, "setCredential", null);
__decorate([
    Delete('providers/:provider/credential'),
    __param(0, Param('provider')),
    __param(1, CurrentUser()),
    __metadata("design:type", Function),
    __metadata("design:paramtypes", [String, Object]),
    __metadata("design:returntype", Object)
], LlmController.prototype, "deleteCredential", null);
__decorate([
    Post('providers/:provider/test'),
    __param(0, Param('provider')),
    __param(1, Body(new ZodPipe(TestLlmCredentialSchema))),
    __param(2, CurrentUser()),
    __metadata("design:type", Function),
    __metadata("design:paramtypes", [String, Object, Object]),
    __metadata("design:returntype", Promise)
], LlmController.prototype, "testCredential", null);
__decorate([
    Get('providers/:provider/models'),
    __param(0, Param('provider')),
    __param(1, CurrentUser()),
    __metadata("design:type", Function),
    __metadata("design:paramtypes", [String, Object]),
    __metadata("design:returntype", Promise)
], LlmController.prototype, "listRemoteModels", null);
LlmController = __decorate([
    Controller('llm'),
    __metadata("design:paramtypes", [OllamaService,
        LlmCredentialsService,
        RemoteProviderService,
        LlmGovernanceService])
], LlmController);
export { LlmController };
function parseProvider(raw) {
    const parsed = RemoteLlmProviderSchema.safeParse(raw);
    if (!parsed.success) {
        throw new BadRequestException({
            code: 'unsupported_provider',
            message: `Unsupported provider '${raw}'. Expected one of: openai, anthropic.`,
        });
    }
    return parsed.data;
}
//# sourceMappingURL=llm.controller.js.map