var __decorate = (this && this.__decorate) || function (decorators, target, key, desc) {
    var c = arguments.length, r = c < 3 ? target : desc === null ? desc = Object.getOwnPropertyDescriptor(target, key) : desc, d;
    if (typeof Reflect === "object" && typeof Reflect.decorate === "function") r = Reflect.decorate(decorators, target, key, desc);
    else for (var i = decorators.length - 1; i >= 0; i--) if (d = decorators[i]) r = (c < 3 ? d(r) : c > 3 ? d(target, key, r) : d(target, key)) || r;
    return c > 3 && r && Object.defineProperty(target, key, r), r;
};
import { Module } from '@nestjs/common';
import { LlmController } from './llm.controller.js';
import { OllamaService } from './ollama.service.js';
import { LlmCredentialsService } from './credentials.service.js';
import { RemoteProviderService } from './remote-provider.service.js';
import { LlmGovernanceService } from './governance.service.js';
let LlmModule = class LlmModule {
};
LlmModule = __decorate([
    Module({
        controllers: [LlmController],
        providers: [OllamaService, LlmCredentialsService, RemoteProviderService, LlmGovernanceService],
        exports: [OllamaService, LlmCredentialsService, RemoteProviderService, LlmGovernanceService],
    })
], LlmModule);
export { LlmModule };
//# sourceMappingURL=llm.module.js.map