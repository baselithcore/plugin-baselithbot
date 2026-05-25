import { SetMetadata } from '@nestjs/common';

export const ALLOW_PASSWORD_CHANGE_KEY = 'dbview:allowPasswordChange';

/**
 * Allows an authenticated route to be reached even when the principal still
 * has `mustChangePassword=true`. Apply to /auth/me, /auth/logout, and
 * /auth/change-password so an invited user can complete the forced reset
 * without being locked out.
 */
export const AllowPasswordChange = (): MethodDecorator & ClassDecorator =>
  SetMetadata(ALLOW_PASSWORD_CHANGE_KEY, true);
