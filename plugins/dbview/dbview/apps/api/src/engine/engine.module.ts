import { Global, Module } from '@nestjs/common';
import { EnginePool } from './engine-pool.js';

@Global()
@Module({
  providers: [EnginePool],
  exports: [EnginePool],
})
export class EngineModule {}
