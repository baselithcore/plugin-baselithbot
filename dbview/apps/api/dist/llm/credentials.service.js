var __decorate = (this && this.__decorate) || function (decorators, target, key, desc) {
    var c = arguments.length, r = c < 3 ? target : desc === null ? desc = Object.getOwnPropertyDescriptor(target, key) : desc, d;
    if (typeof Reflect === "object" && typeof Reflect.decorate === "function") r = Reflect.decorate(decorators, target, key, desc);
    else for (var i = decorators.length - 1; i >= 0; i--) if (d = decorators[i]) r = (c < 3 ? d(r) : c > 3 ? d(target, key, r) : d(target, key)) || r;
    return c > 3 && r && Object.defineProperty(target, key, r), r;
};
import { Injectable, Logger } from '@nestjs/common';
import { decryptString, encryptString } from '../connections/crypto.js';
import { LlmCredentialsStore } from './credentials.store.js';
/**
 * Per-user encrypted LLM API key storage.
 *
 * Keys are stored ciphered at rest (AES-256-GCM via the shared `DBVIEW_SECRET`),
 * the same pattern used by database connection strings.
 *
 * Resolution order at adapter-build time:
 *   1. Per-user stored key (decrypted on demand, kept in memory only for the
 *      duration of the request).
 *   2. Process env (`OPENAI_API_KEY` / `ANTHROPIC_API_KEY`) — preserved as a
 *      fallback so existing deployments keep working without re-onboarding,
 *      and so the service-to-service synthetic admin (api-key guard) still
 *      authenticates remote providers.
 */
let LlmCredentialsService = class LlmCredentialsService {
    logger = new Logger('LlmCredentialsService');
    store = new LlmCredentialsStore();
    status(provider, principal) {
        const stored = this.store.get(principal.id, provider);
        if (stored) {
            return {
                provider,
                hasKey: true,
                envFallback: false,
                maskedTail: stored.maskedTail,
                updatedAt: stored.updatedAt,
            };
        }
        const envKey = readEnvKey(provider);
        if (envKey) {
            return {
                provider,
                hasKey: true,
                envFallback: true,
                maskedTail: tail(envKey),
            };
        }
        return { provider, hasKey: false, envFallback: false };
    }
    upsert(provider, apiKey, principal) {
        const now = new Date().toISOString();
        const existing = this.store.get(principal.id, provider);
        const next = {
            userId: principal.id,
            provider,
            cipher: encryptString(apiKey),
            maskedTail: tail(apiKey),
            createdAt: existing?.createdAt ?? now,
            updatedAt: now,
        };
        this.store.upsert(next);
        this.logger.log(`credential_${existing ? 'updated' : 'created'} user=${principal.id} provider=${provider}`);
        return {
            provider,
            hasKey: true,
            envFallback: false,
            maskedTail: next.maskedTail,
            updatedAt: next.updatedAt,
        };
    }
    remove(provider, principal) {
        const removed = this.store.remove(principal.id, provider);
        if (removed) {
            this.logger.log(`credential_removed user=${principal.id} provider=${provider}`);
        }
        return this.status(provider, principal);
    }
    /**
     * Resolve the API key to use for an outgoing request. Per-user stored key
     * wins over env. Returns `undefined` when neither is configured — callers
     * must handle the "no key" case so the SDK doesn't silently send unauth'd
     * requests that fail with a generic 401.
     */
    resolveApiKey(provider, principal) {
        const stored = this.store.get(principal.id, provider);
        if (stored) {
            try {
                return decryptString(stored.cipher);
            }
            catch (err) {
                this.logger.error(`credential_decrypt_failed user=${principal.id} provider=${provider}: ${err.message}`);
            }
        }
        return readEnvKey(provider);
    }
};
LlmCredentialsService = __decorate([
    Injectable()
], LlmCredentialsService);
export { LlmCredentialsService };
function readEnvKey(provider) {
    const raw = provider === 'openai' ? process.env.OPENAI_API_KEY : process.env.ANTHROPIC_API_KEY;
    return raw && raw.trim().length > 0 ? raw.trim() : undefined;
}
function tail(s) {
    return s.length <= 4 ? '••••' : `••••${s.slice(-4)}`;
}
//# sourceMappingURL=credentials.service.js.map