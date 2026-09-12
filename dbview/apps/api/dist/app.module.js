var __decorate = (this && this.__decorate) || function (decorators, target, key, desc) {
    var c = arguments.length, r = c < 3 ? target : desc === null ? desc = Object.getOwnPropertyDescriptor(target, key) : desc, d;
    if (typeof Reflect === "object" && typeof Reflect.decorate === "function") r = Reflect.decorate(decorators, target, key, desc);
    else for (var i = decorators.length - 1; i >= 0; i--) if (d = decorators[i]) r = (c < 3 ? d(r) : c > 3 ? d(target, key, r) : d(target, key)) || r;
    return c > 3 && r && Object.defineProperty(target, key, r), r;
};
import { Module } from '@nestjs/common';
import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';
import { ConfigModule } from '@nestjs/config';
import { LoggerModule } from 'nestjs-pino';
import { ConnectionsModule } from './connections/connections.module.js';
import { SchemaModule } from './schema/schema.module.js';
import { Nl2SqlModule } from './nl2sql/nl2sql.module.js';
import { QueryModule } from './query/query.module.js';
import { HealthModule } from './health/health.module.js';
import { LlmModule } from './llm/llm.module.js';
import { HistoryModule } from './history/history.module.js';
import { ApiKeyGuard } from './common/api-key.guard.js';
import { AuthModule } from './auth/auth.module.js';
import { GatewayAuthGuard } from './auth/gateway-auth.guard.js';
import { JwtAuthGuard } from './auth/jwt-auth.guard.js';
import { RolesGuard } from './auth/roles.guard.js';
import { EngineModule } from './engine/engine.module.js';
import { ObservabilityModule } from './observability/observability.module.js';
import { MetricsInterceptor } from './observability/metrics.interceptor.js';
import { LlmUsageInterceptor } from './observability/llm-usage.interceptor.js';
import { currentRequestId, newRequestId } from './common/request-context.js';
import { APP_GUARD, APP_INTERCEPTOR } from '@nestjs/core';
let AppModule = class AppModule {
};
AppModule = __decorate([
    Module({
        imports: [
            ConfigModule.forRoot({
                isGlobal: true,
                envFilePath: [
                    resolve(dirname(fileURLToPath(import.meta.url)), '../.env'),
                    resolve(process.cwd(), 'apps/api/.env'),
                    resolve(process.cwd(), '.env'),
                ],
            }),
            LoggerModule.forRoot({
                pinoHttp: {
                    level: process.env.LOG_LEVEL ?? (process.env.NODE_ENV === 'production' ? 'info' : 'debug'),
                    autoLogging: {
                        ignore: (req) => req.url === '/api/health' || req.url === '/api/metrics',
                    },
                    genReqId: (req) => newRequestId(req.headers['x-request-id'] ?? null),
                    customProps: () => {
                        const rid = currentRequestId();
                        return rid ? { request_id: rid } : {};
                    },
                    redact: {
                        paths: [
                            'req.headers.authorization',
                            'req.headers["x-api-key"]',
                            'req.headers.cookie',
                            'res.headers["set-cookie"]',
                            'connectionString',
                            'connectionStringCipher',
                            'password',
                            'passwordHash',
                            'accessToken',
                            'refreshToken',
                            'clientSecret',
                            'apiKey',
                        ],
                        censor: '[redacted]',
                    },
                    transport: process.env.NODE_ENV !== 'production' && process.env.LOG_FORMAT !== 'json'
                        ? { target: 'pino-pretty', options: { singleLine: true } }
                        : undefined,
                },
            }),
            ObservabilityModule,
            EngineModule,
            HealthModule,
            AuthModule,
            LlmModule,
            ConnectionsModule,
            SchemaModule,
            Nl2SqlModule,
            QueryModule,
            HistoryModule,
        ],
        providers: [
            // GatewayAuthGuard first: a trusted-proxy identity short-circuits the JWT
            // guard exactly like ApiKeyGuard's synthetic principal. Inert (returns
            // true immediately) unless DBVIEW_GATEWAY_AUTH + DBVIEW_GATEWAY_SECRET
            // are configured, so standalone behaviour is unchanged.
            { provide: APP_GUARD, useClass: GatewayAuthGuard },
            { provide: APP_GUARD, useClass: ApiKeyGuard },
            { provide: APP_GUARD, useClass: JwtAuthGuard },
            { provide: APP_GUARD, useClass: RolesGuard },
            { provide: APP_INTERCEPTOR, useClass: MetricsInterceptor },
            { provide: APP_INTERCEPTOR, useClass: LlmUsageInterceptor },
        ],
    })
], AppModule);
export { AppModule };
//# sourceMappingURL=app.module.js.map