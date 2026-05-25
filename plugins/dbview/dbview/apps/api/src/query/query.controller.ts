import { Body, Controller, Post } from '@nestjs/common';
import {
  ExecuteQueryRequestSchema,
  SampleRequestSchema,
  type ExecuteQueryResponse,
} from '@dbview/shared';
import { ZodPipe } from '../common/zod.pipe.js';
import { CurrentUser } from '../auth/decorators.js';
import type { AuthPrincipal } from '../auth/auth.types.js';
import { QueryService } from './query.service.js';

@Controller('query')
export class QueryController {
  constructor(private readonly svc: QueryService) {}

  @Post('execute')
  execute(
    @Body(new ZodPipe(ExecuteQueryRequestSchema)) body: unknown,
    @CurrentUser() principal: AuthPrincipal
  ): Promise<ExecuteQueryResponse> {
    return this.svc.execute(body as never, principal);
  }

  @Post('sample')
  sample(
    @Body(new ZodPipe(SampleRequestSchema)) body: unknown,
    @CurrentUser() principal: AuthPrincipal
  ): Promise<ExecuteQueryResponse> {
    return this.svc.sample(body as never, principal);
  }
}
