import { Module } from '@nestjs/common';
import { ConnectionsModule } from '../connections/connections.module.js';
import { SchemaModule } from '../schema/schema.module.js';
import { QueryModule } from '../query/query.module.js';
import { HistoryModule } from '../history/history.module.js';
import { LlmModule } from '../llm/llm.module.js';
import { Nl2SqlController } from './nl2sql.controller.js';
import { Nl2SqlService } from './nl2sql.service.js';
import { Nl2QueryAskService } from './ask.service.js';

@Module({
  imports: [ConnectionsModule, SchemaModule, QueryModule, HistoryModule, LlmModule],
  controllers: [Nl2SqlController],
  providers: [Nl2SqlService, Nl2QueryAskService],
})
export class Nl2SqlModule {}
