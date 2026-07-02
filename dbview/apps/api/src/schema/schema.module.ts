import { Module } from '@nestjs/common';
import { ConnectionsModule } from '../connections/connections.module.js';
import { SchemaController } from './schema.controller.js';
import { SchemaService } from './schema.service.js';

@Module({
  imports: [ConnectionsModule],
  controllers: [SchemaController],
  providers: [SchemaService],
  exports: [SchemaService],
})
export class SchemaModule {}
