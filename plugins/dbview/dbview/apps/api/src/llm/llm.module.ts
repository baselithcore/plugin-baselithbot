import { Module } from '@nestjs/common';
import { LlmController } from './llm.controller.js';
import { OllamaService } from './ollama.service.js';
import { LlmCredentialsService } from './credentials.service.js';
import { RemoteProviderService } from './remote-provider.service.js';

@Module({
  controllers: [LlmController],
  providers: [OllamaService, LlmCredentialsService, RemoteProviderService],
  exports: [OllamaService, LlmCredentialsService, RemoteProviderService],
})
export class LlmModule {}
