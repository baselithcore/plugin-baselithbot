import { type InviteRequest, type UpdateUserRequest, type UserPublic } from '@dbview/shared';
import { AuthService } from './auth.service.js';
import type { AuthPrincipal } from './auth.types.js';
export declare class UsersController {
    private readonly auth;
    constructor(auth: AuthService);
    list(actor: AuthPrincipal): UserPublic[];
    invite(body: InviteRequest, actor: AuthPrincipal): Promise<UserPublic>;
    update(id: string, body: UpdateUserRequest, actor: AuthPrincipal): Promise<UserPublic>;
    remove(id: string, actor: AuthPrincipal): {
        ok: true;
    };
}
//# sourceMappingURL=users.controller.d.ts.map