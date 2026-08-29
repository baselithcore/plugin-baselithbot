export function toPublicUser(u) {
    return {
        id: u.id,
        email: u.email,
        displayName: u.displayName,
        role: u.role,
        isActive: u.isActive,
        createdAt: u.createdAt,
        lastLoginAt: u.lastLoginAt,
        mustChangePassword: u.mustChangePassword,
    };
}
//# sourceMappingURL=auth.types.js.map