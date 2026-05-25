import { Controller, Get, Header } from '@nestjs/common';
import { Roles } from '../auth/decorators.js';
import { registry } from './metrics.registry.js';

@Controller('metrics')
@Roles('admin')
export class MetricsController {
  @Get()
  @Header('Content-Type', 'text/plain; version=0.0.4; charset=utf-8')
  scrape(): Promise<string> {
    return registry.metrics();
  }
}
