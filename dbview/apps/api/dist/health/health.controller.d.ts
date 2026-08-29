interface DependencyResult {
    name: string;
    required: boolean;
    ready: boolean;
    status: 'ok' | 'error' | 'disabled';
    error?: string;
}
interface ReadyResponse {
    status: 'ok' | 'degraded';
    ready: boolean;
    uptime: number;
    version: string;
    dependencies: Record<string, DependencyResult>;
}
export declare class HealthController {
    health(): {
        status: 'ok';
        uptime: number;
        version: string;
    };
    live(): {
        status: 'alive';
    };
    ready(): ReadyResponse;
    private checkDataDir;
    private checkJwtSecret;
    private checkEncryptionSecret;
}
export {};
//# sourceMappingURL=health.controller.d.ts.map