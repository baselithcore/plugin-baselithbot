export declare const ALLOW_PASSWORD_CHANGE_KEY = "dbview:allowPasswordChange";
/**
 * Allows an authenticated route to be reached even when the principal still
 * has `mustChangePassword=true`. Apply to /auth/me, /auth/logout, and
 * /auth/change-password so an invited user can complete the forced reset
 * without being locked out.
 */
export declare const AllowPasswordChange: () => MethodDecorator & ClassDecorator;
//# sourceMappingURL=password-change.decorator.d.ts.map