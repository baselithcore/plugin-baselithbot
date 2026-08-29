import { CallHandler, ExecutionContext, NestInterceptor } from '@nestjs/common';
import { Observable } from 'rxjs';
export declare class MetricsInterceptor implements NestInterceptor {
    intercept(ctx: ExecutionContext, next: CallHandler): Observable<unknown>;
}
//# sourceMappingURL=metrics.interceptor.d.ts.map