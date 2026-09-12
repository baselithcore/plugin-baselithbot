import { CallHandler, ExecutionContext, NestInterceptor } from '@nestjs/common';
import { Observable } from 'rxjs';
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
export declare class LlmUsageInterceptor implements NestInterceptor {
    intercept(ctx: ExecutionContext, next: CallHandler): Observable<unknown>;
}
//# sourceMappingURL=llm-usage.interceptor.d.ts.map