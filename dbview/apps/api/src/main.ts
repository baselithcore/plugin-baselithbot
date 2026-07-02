import 'reflect-metadata';
import './observability/otel.js'; // must be first to instrument Node modules
import { NestFactory } from '@nestjs/core';
import { FastifyAdapter, type NestFastifyApplication } from '@nestjs/platform-fastify';
import fastifyCookie from '@fastify/cookie';
import fastifyCompress from '@fastify/compress';
import { Logger } from 'nestjs-pino';
import { AppModule } from './app.module.js';
import { DbviewExceptionFilter } from './common/dbview-exception.filter.js';
import { newRequestId, runWithContext } from './common/request-context.js';

async function bootstrap(): Promise<void> {
  const app = await NestFactory.create<NestFastifyApplication>(
    AppModule,
    new FastifyAdapter({
      trustProxy: true,
      logger: false,
      bodyLimit: Number(process.env.DBVIEW_BODY_LIMIT) || 400 * 1024 * 1024,
    }),
    { bufferLogs: true },
  );
  app.useLogger(app.get(Logger));
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  await app.register(fastifyCookie as any);
  // Response compression. Wide-schema introspection results can exceed 1MB of
  // JSON; gzip typically reduces that by ~80% on the wire. Threshold 1KB keeps
  // small handshake responses uncompressed.
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  await app.register(fastifyCompress as any, {
    threshold: 1024,
    encodings: ['br', 'gzip', 'deflate'],
  });
  const fastify = app.getHttpAdapter().getInstance();
  fastify.addHook('onRequest', (req, reply, done) => {
    const incoming = (req.headers['x-request-id'] as string | undefined) ?? null;
    const requestId = newRequestId(incoming);
    reply.header('x-request-id', requestId);
    runWithContext({ requestId }, () => done());
  });
  app.enableCors({
    origin: true,
    credentials: true,
    exposedHeaders: ['x-request-id'],
  });
  app.setGlobalPrefix('api');
  app.useGlobalFilters(new DbviewExceptionFilter());
  const port = Number(process.env.PORT) || 3001;
  await app.listen(port, '0.0.0.0');
  app.get(Logger).log(`[dbview-api] listening on :${port}`);
}

bootstrap().catch((err) => {
  process.stderr.write(`Bootstrap failed: ${(err as Error).stack ?? err}\n`);
  process.exit(1);
});
