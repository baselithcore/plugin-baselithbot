import { ArgumentsHost, Catch, ExceptionFilter, HttpException, Logger } from '@nestjs/common';
import { ConnectionUnreachableError, DbviewError, SchemaMismatchError } from '@dbview/shared';
import type { FastifyReply } from 'fastify';

@Catch()
export class DbviewExceptionFilter implements ExceptionFilter {
  private readonly logger = new Logger('DbviewExceptionFilter');

  catch(exception: unknown, host: ArgumentsHost): void {
    const ctx = host.switchToHttp();
    const reply = ctx.getResponse<FastifyReply>();

    if (exception instanceof DbviewError) {
      this.logger.warn(
        `[${exception.code}] ${exception.message}${exception.stack ? `\n${exception.stack}` : ''}`
      );
      const body: Record<string, unknown> = {
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

    const err = exception as Error;
    this.logger.error(err.stack ?? err.message ?? String(err));
    const detail = extractMessage(exception);
    reply.status(500).send({
      code: 'internal_error',
      message: process.env.NODE_ENV === 'production' ? 'Internal server error' : detail,
    });
  }
}

function extractMessage(err: unknown): string {
  if (err instanceof AggregateError) {
    const inner = err.errors
      .map((e) => (e as { message?: string }).message ?? String(e))
      .filter((m) => m && m.length > 0);
    const code = (err as { code?: string }).code;
    const detail = inner.join('; ') || 'aggregate error';
    return code ? `${code}: ${detail}` : detail;
  }
  if (err instanceof Error) {
    const code = (err as { code?: string }).code;
    return code && err.message ? `${code}: ${err.message}` : err.message || err.name;
  }
  return String(err);
}
