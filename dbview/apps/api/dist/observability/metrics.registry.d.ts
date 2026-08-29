import { Counter, Gauge, Histogram, Registry } from 'prom-client';
export declare const registry: Registry<"text/plain; version=0.0.4; charset=utf-8">;
export declare const httpRequestLatency: Histogram<"method" | "route" | "status_bucket">;
export declare const httpRequestErrors: Counter<"method" | "route" | "status_bucket" | "reason">;
export declare const llmCalls: Counter<"mode" | "status" | "provider" | "model">;
export declare const llmCallLatency: Histogram<"mode" | "provider" | "model">;
export declare const llmTokens: Counter<"type" | "provider" | "model">;
export declare const queryExecutions: Counter<"status" | "dialect">;
export declare const queryExecutionLatency: Histogram<"dialect">;
export declare const introspectionFailures: Counter<"reason" | "dialect">;
export declare const authEvents: Counter<"event">;
export declare const connectionsUp: Gauge<"dialect" | "connection_id">;
export declare function statusBucket(status: number): string;
//# sourceMappingURL=metrics.registry.d.ts.map