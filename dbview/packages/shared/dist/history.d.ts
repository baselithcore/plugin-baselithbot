import { z } from 'zod';
/**
 * Persisted record of a single NL2Query turn. Captures prompt, generated
 * query, outcome (rows + duration or error code), and a favorite flag the
 * user can toggle from the UI.
 */
export declare const HistoryEntrySchema: z.ZodObject<{
    id: z.ZodString;
    ownerId: z.ZodString;
    connectionId: z.ZodString;
    connectionName: z.ZodString;
    prompt: z.ZodString;
    query: z.ZodString;
    language: z.ZodEnum<["sql", "cypher", "qdrant", "soql"]>;
    provider: z.ZodString;
    model: z.ZodString;
    summary: z.ZodNullable<z.ZodString>;
    rowCount: z.ZodNullable<z.ZodNumber>;
    durationMs: z.ZodNullable<z.ZodNumber>;
    ok: z.ZodBoolean;
    errorCode: z.ZodNullable<z.ZodString>;
    errorMessage: z.ZodNullable<z.ZodString>;
    favorite: z.ZodBoolean;
    createdAt: z.ZodString;
}, "strip", z.ZodTypeAny, {
    id: string;
    createdAt: string;
    ownerId: string;
    prompt: string;
    query: string;
    language: "qdrant" | "sql" | "cypher" | "soql";
    rowCount: number | null;
    ok: boolean;
    connectionId: string;
    provider: string;
    model: string;
    durationMs: number | null;
    summary: string | null;
    connectionName: string;
    errorCode: string | null;
    errorMessage: string | null;
    favorite: boolean;
}, {
    id: string;
    createdAt: string;
    ownerId: string;
    prompt: string;
    query: string;
    language: "qdrant" | "sql" | "cypher" | "soql";
    rowCount: number | null;
    ok: boolean;
    connectionId: string;
    provider: string;
    model: string;
    durationMs: number | null;
    summary: string | null;
    connectionName: string;
    errorCode: string | null;
    errorMessage: string | null;
    favorite: boolean;
}>;
export type HistoryEntry = z.infer<typeof HistoryEntrySchema>;
export declare const CreateHistoryEntryDtoSchema: z.ZodObject<Omit<{
    id: z.ZodString;
    ownerId: z.ZodString;
    connectionId: z.ZodString;
    connectionName: z.ZodString;
    prompt: z.ZodString;
    query: z.ZodString;
    language: z.ZodEnum<["sql", "cypher", "qdrant", "soql"]>;
    provider: z.ZodString;
    model: z.ZodString;
    summary: z.ZodNullable<z.ZodString>;
    rowCount: z.ZodNullable<z.ZodNumber>;
    durationMs: z.ZodNullable<z.ZodNumber>;
    ok: z.ZodBoolean;
    errorCode: z.ZodNullable<z.ZodString>;
    errorMessage: z.ZodNullable<z.ZodString>;
    favorite: z.ZodBoolean;
    createdAt: z.ZodString;
}, "id" | "createdAt" | "ownerId" | "favorite">, "strip", z.ZodTypeAny, {
    prompt: string;
    query: string;
    language: "qdrant" | "sql" | "cypher" | "soql";
    rowCount: number | null;
    ok: boolean;
    connectionId: string;
    provider: string;
    model: string;
    durationMs: number | null;
    summary: string | null;
    connectionName: string;
    errorCode: string | null;
    errorMessage: string | null;
}, {
    prompt: string;
    query: string;
    language: "qdrant" | "sql" | "cypher" | "soql";
    rowCount: number | null;
    ok: boolean;
    connectionId: string;
    provider: string;
    model: string;
    durationMs: number | null;
    summary: string | null;
    connectionName: string;
    errorCode: string | null;
    errorMessage: string | null;
}>;
export type CreateHistoryEntryDto = z.infer<typeof CreateHistoryEntryDtoSchema>;
export declare const ListHistoryQuerySchema: z.ZodObject<{
    connectionId: z.ZodOptional<z.ZodString>;
    favoritesOnly: z.ZodOptional<z.ZodBoolean>;
    limit: z.ZodDefault<z.ZodNumber>;
    offset: z.ZodDefault<z.ZodNumber>;
}, "strip", z.ZodTypeAny, {
    limit: number;
    offset: number;
    connectionId?: string | undefined;
    favoritesOnly?: boolean | undefined;
}, {
    connectionId?: string | undefined;
    favoritesOnly?: boolean | undefined;
    limit?: number | undefined;
    offset?: number | undefined;
}>;
export type ListHistoryQuery = z.infer<typeof ListHistoryQuerySchema>;
export declare const ListHistoryResponseSchema: z.ZodObject<{
    entries: z.ZodArray<z.ZodObject<{
        id: z.ZodString;
        ownerId: z.ZodString;
        connectionId: z.ZodString;
        connectionName: z.ZodString;
        prompt: z.ZodString;
        query: z.ZodString;
        language: z.ZodEnum<["sql", "cypher", "qdrant", "soql"]>;
        provider: z.ZodString;
        model: z.ZodString;
        summary: z.ZodNullable<z.ZodString>;
        rowCount: z.ZodNullable<z.ZodNumber>;
        durationMs: z.ZodNullable<z.ZodNumber>;
        ok: z.ZodBoolean;
        errorCode: z.ZodNullable<z.ZodString>;
        errorMessage: z.ZodNullable<z.ZodString>;
        favorite: z.ZodBoolean;
        createdAt: z.ZodString;
    }, "strip", z.ZodTypeAny, {
        id: string;
        createdAt: string;
        ownerId: string;
        prompt: string;
        query: string;
        language: "qdrant" | "sql" | "cypher" | "soql";
        rowCount: number | null;
        ok: boolean;
        connectionId: string;
        provider: string;
        model: string;
        durationMs: number | null;
        summary: string | null;
        connectionName: string;
        errorCode: string | null;
        errorMessage: string | null;
        favorite: boolean;
    }, {
        id: string;
        createdAt: string;
        ownerId: string;
        prompt: string;
        query: string;
        language: "qdrant" | "sql" | "cypher" | "soql";
        rowCount: number | null;
        ok: boolean;
        connectionId: string;
        provider: string;
        model: string;
        durationMs: number | null;
        summary: string | null;
        connectionName: string;
        errorCode: string | null;
        errorMessage: string | null;
        favorite: boolean;
    }>, "many">;
    total: z.ZodNumber;
}, "strip", z.ZodTypeAny, {
    entries: {
        id: string;
        createdAt: string;
        ownerId: string;
        prompt: string;
        query: string;
        language: "qdrant" | "sql" | "cypher" | "soql";
        rowCount: number | null;
        ok: boolean;
        connectionId: string;
        provider: string;
        model: string;
        durationMs: number | null;
        summary: string | null;
        connectionName: string;
        errorCode: string | null;
        errorMessage: string | null;
        favorite: boolean;
    }[];
    total: number;
}, {
    entries: {
        id: string;
        createdAt: string;
        ownerId: string;
        prompt: string;
        query: string;
        language: "qdrant" | "sql" | "cypher" | "soql";
        rowCount: number | null;
        ok: boolean;
        connectionId: string;
        provider: string;
        model: string;
        durationMs: number | null;
        summary: string | null;
        connectionName: string;
        errorCode: string | null;
        errorMessage: string | null;
        favorite: boolean;
    }[];
    total: number;
}>;
export type ListHistoryResponse = z.infer<typeof ListHistoryResponseSchema>;
export declare const ToggleFavoriteDtoSchema: z.ZodObject<{
    favorite: z.ZodBoolean;
}, "strip", z.ZodTypeAny, {
    favorite: boolean;
}, {
    favorite: boolean;
}>;
export type ToggleFavoriteDto = z.infer<typeof ToggleFavoriteDtoSchema>;
//# sourceMappingURL=history.d.ts.map