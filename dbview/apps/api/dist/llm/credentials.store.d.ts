import type { RemoteLlmProvider } from '@dbview/shared';
export interface StoredCredential {
    userId: string;
    provider: RemoteLlmProvider;
    cipher: string;
    /** Last 4 chars of the plaintext key (UI-only hint). Never the full key. */
    maskedTail: string;
    createdAt: string;
    updatedAt: string;
}
/**
 * Persistence layer for per-user LLM API keys.
 *
 * On-disk shape mirrors connections.json: atomic write via tmp+rename, mode
 * 0600, JSON. Ciphertext only — plaintext keys are never written. Decryption
 * happens in {@link LlmCredentialsService}, not here.
 */
export declare class LlmCredentialsStore {
    private readonly filePath;
    /** key = `${userId}:${provider}` */
    private credentials;
    constructor(filePath?: string);
    get(userId: string, provider: RemoteLlmProvider): StoredCredential | undefined;
    upsert(c: StoredCredential): void;
    remove(userId: string, provider: RemoteLlmProvider): boolean;
    private load;
    private persist;
}
//# sourceMappingURL=credentials.store.d.ts.map