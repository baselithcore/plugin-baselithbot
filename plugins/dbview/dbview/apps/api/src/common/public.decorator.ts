import { SetMetadata } from '@nestjs/common';

export const IS_PUBLIC_KEY = 'dbview:isPublic';

/**
 * Marks a route handler (or controller) as exempt from auth guards.
 * Used by `ApiKeyGuard` to skip key verification on truly public endpoints
 * (e.g. /health). Prefer this over URL string matching.
 */
export const Public = (): MethodDecorator & ClassDecorator => SetMetadata(IS_PUBLIC_KEY, true);
