import { Module } from '@nestjs/common';
import { ConnectionsModule } from '../connections/connections.module.js';
import { SchemaModule } from '../schema/schema.module.js';
import { QueryController } from './query.controller.js';
import { QueryService } from './query.service.js';

@Module({
  imports: [ConnectionsModule, SchemaModule],
  controllers: [QueryController],
  providers: [QueryService],
  exports: [QueryService],
})
export class QueryModule {}
