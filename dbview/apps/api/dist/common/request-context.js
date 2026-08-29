import { AsyncLocalStorage } from 'node:async_hooks';
import { randomUUID } from 'node:crypto';
const storage = new AsyncLocalStorage();
export function runWithContext(ctx, fn) {
    return storage.run(ctx, fn);
}
export function currentRequestId() {
    return storage.getStore()?.requestId;
}
/** The live LLM governance for the current request, or `undefined`. */
export function currentGovernance() {
    return storage.getStore()?.governance;
}
export function newRequestId(existing) {
    if (existing && existing.length > 0 && existing.length <= 128)
        return existing;
    return randomUUID();
}
//# sourceMappingURL=request-context.js.map