import { Module } from '@nestjs/common';
import { LlmController } from './llm.controller.js';
import { OllamaService } from './ollama.service.js';
import { LlmCredentialsService } from './credentials.service.js';
import { RemoteProviderService } from './remote-provider.service.js';
import { LlmGovernanceService } from './governance.service.js';

@Module({
  controllers: [LlmController],
  providers: [OllamaService, LlmCredentialsService, RemoteProviderService, LlmGovernanceService],
  exports: [OllamaService, LlmCredentialsService, RemoteProviderService, LlmGovernanceService],
})
export class LlmModule {}
