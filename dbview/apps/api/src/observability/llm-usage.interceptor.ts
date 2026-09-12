import { CallHandler, ExecutionContext, Injectable, NestInterceptor } from '@nestjs/common';
import { Observable, tap } from 'rxjs';
import type { FastifyReply } from 'fastify';
import {
  USAGE_HEADER,
  serializeUsage,
  withUsageCapture,
  type UsageRow,
} from './llm-usage.store.js';

/**
 * Report the tokens a request spent back to the gateway.
 *
 * The handler runs inside a per-request usage accumulator (subscription happens
 * *inside* `withUsageCapture`, so the async context reaches the adapters), and
 * whatever the providers reported is stamped on the response as
 * `x-dbview-llm-usage` before it is sent. The gateway then attributes it to the
 * caller and forwards it to the framework's token seam — without this the host
 * sees none of the child's spend and every dbview cost figure reads zero.
 *
 * Streamed responses are not covered: headers are already flushed when the
 * first chunk goes out, so their usage is simply not reported rather than
 * reported late or guessed.
 */
@Injectable()
export class LlmUsageInterceptor implements NestInterceptor {
  intercept(ctx: ExecutionContext, next: CallHandler): Observable<unknown> {
    if (ctx.getType() !== 'http') return next.handle();
    const reply = ctx.switchToHttp().getResponse<FastifyReply>();
    const rows: UsageRow[] = [];

    return new Observable((subscriber) =>
      withUsageCapture(rows, () =>
        next
          .handle()
          .pipe(
            tap({
              next: () => stamp(reply, rows),
              error: () => stamp(reply, rows),
            })
          )
          .subscribe(subscriber)
      )
    );
  }
}

function stamp(reply: FastifyReply, rows: readonly UsageRow[]): void {
  const value = serializeUsage(rows);
  if (!value) return;
  try {
    // `reply.raw.headersSent` rather than the deprecated `reply.sent`: same
    // answer on Fastify 4 and still there on 5.
    if (!reply.raw.headersSent) reply.header(USAGE_HEADER, value);
  } catch {
    // Accounting must never break a response: a reply already on the wire
    // simply carries no usage header.
  }
}
