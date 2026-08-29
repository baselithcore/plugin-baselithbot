import { z } from 'zod';
import { QueryLanguageSchema } from './nl2sql.js';
/**
 * Persisted record of a single NL2Query turn. Captures prompt, generated
 * query, outcome (rows + duration or error code), and a favorite flag the
 * user can toggle from the UI.
 */
export const HistoryEntrySchema = z.object({
    id: z.string().uuid(),
    ownerId: z.string().uuid(),
    connectionId: z.string().uuid(),
    connectionName: z.string(),
    prompt: z.string(),
    query: z.string(),
    language: QueryLanguageSchema,
    provider: z.string(),
    model: z.string(),
    summary: z.string().nullable(),
    rowCount: z.number().int().nonnegative().nullable(),
    durationMs: z.number().int().nonnegative().nullable(),
    ok: z.boolean(),
    errorCode: z.string().nullable(),
    errorMessage: z.string().nullable(),
    favorite: z.boolean(),
    createdAt: z.string(), // ISO 8601
});
export const CreateHistoryEntryDtoSchema = HistoryEntrySchema.omit({
    id: true,
    ownerId: true,
    createdAt: true,
    favorite: true,
});
export const ListHistoryQuerySchema = z.object({
    connectionId: z.string().uuid().optional(),
    favoritesOnly: z.coerce.boolean().optional(),
    limit: z.coerce.number().int().positive().max(500).default(100),
    offset: z.coerce.number().int().nonnegative().default(0),
});
export const ListHistoryResponseSchema = z.object({
    entries: z.array(HistoryEntrySchema),
    total: z.number().int().nonnegative(),
});
export const ToggleFavoriteDtoSchema = z.object({
    favorite: z.boolean(),
});
//# sourceMappingURL=history.js.map