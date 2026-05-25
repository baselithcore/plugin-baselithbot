import { Body, Controller, Post, UseGuards } from '@nestjs/common';
import {
  Nl2QueryAskRequestSchema,
  Nl2SqlRequestSchema,
  type Nl2QueryAskResponse,
  type Nl2SqlResponse,
} from '@dbview/shared';
import { ZodPipe } from '../common/zod.pipe.js';
import { RateLimit, RateLimitGuard } from '../common/rate-limit.guard.js';
import { CurrentUser } from '../auth/decorators.js';
import type { AuthPrincipal } from '../auth/auth.types.js';
import { Nl2SqlService } from './nl2sql.service.js';
import { Nl2QueryAskService } from './ask.service.js';

@Controller('nl2sql')
@UseGuards(RateLimitGuard)
export class Nl2SqlController {
  constructor(
    private readonly svc: Nl2SqlService,
    private readonly ask: Nl2QueryAskService,
  ) {}

  @Post()
  @RateLimit({ limit: 20, windowSec: 60 })
  translate(
    @Body(new ZodPipe(Nl2SqlRequestSchema)) body: unknown,
    @CurrentUser() principal: AuthPrincipal,
  ): Promise<Nl2SqlResponse> {
    return this.svc.translate(body as never, principal);
  }

  @Post('ask')
  @RateLimit({ limit: 20, windowSec: 60 })
  askEndpoint(
    @Body(new ZodPipe(Nl2QueryAskRequestSchema)) body: unknown,
    @CurrentUser() principal: AuthPrincipal,
  ): Promise<Nl2QueryAskResponse> {
    return this.ask.ask(body as never, principal);
  }
}
