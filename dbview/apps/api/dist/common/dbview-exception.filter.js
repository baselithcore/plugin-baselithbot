var __decorate = (this && this.__decorate) || function (decorators, target, key, desc) {
    var c = arguments.length, r = c < 3 ? target : desc === null ? desc = Object.getOwnPropertyDescriptor(target, key) : desc, d;
    if (typeof Reflect === "object" && typeof Reflect.decorate === "function") r = Reflect.decorate(decorators, target, key, desc);
    else for (var i = decorators.length - 1; i >= 0; i--) if (d = decorators[i]) r = (c < 3 ? d(r) : c > 3 ? d(target, key, r) : d(target, key)) || r;
    return c > 3 && r && Object.defineProperty(target, key, r), r;
};
import { Catch, HttpException, Logger } from '@nestjs/common';
import { ConnectionUnreachableError, DbviewError, SchemaMismatchError } from '@dbview/shared';
let DbviewExceptionFilter = class DbviewExceptionFilter {
    logger = new Logger('DbviewExceptionFilter');
    catch(exception, host) {
        const ctx = host.switchToHttp();
        const reply = ctx.getResponse();
        if (exception instanceof DbviewError) {
            this.logger.warn(`[${exception.code}] ${exception.message}${exception.stack ? `\n${exception.stack}` : ''}`);
            const body = {
                code: exception.code,
                message: exception.message,
            };
            if (exception instanceof SchemaMismatchError) {
                body.details = exception.details;
            }
            if (exception instanceof ConnectionUnreachableError) {
                body.details = exception.details;
            }
            reply.status(exception.status).send(body);
            return;
        }
        if (exception instanceof HttpException) {
            const status = exception.getStatus();
            const body = exception.getResponse();
            reply.status(status).send(typeof body === 'string' ? { message: body } : body);
            return;
        }
        const err = exception;
        this.logger.error(err.stack ?? err.message ?? String(err));
        const detail = extractMessage(exception);
        reply.status(500).send({
            code: 'internal_error',
            message: process.env.NODE_ENV === 'production' ? 'Internal server error' : detail,
        });
    }
};
DbviewExceptionFilter = __decorate([
    Catch()
], DbviewExceptionFilter);
export { DbviewExceptionFilter };
function extractMessage(err) {
    if (err instanceof AggregateError) {
        const inner = err.errors
            .map((e) => e.message ?? String(e))
            .filter((m) => m && m.length > 0);
        const code = err.code;
        const detail = inner.join('; ') || 'aggregate error';
        return code ? `${code}: ${detail}` : detail;
    }
    if (err instanceof Error) {
        const code = err.code;
        return code && err.message ? `${code}: ${err.message}` : err.message || err.name;
    }
    return String(err);
}
//# sourceMappingURL=dbview-exception.filter.js.map