import { Reflector } from '@nestjs/core';
import { type AuthConfig, type ChangePasswordRequest, type LoginRequest, type LoginResponse, type MeResponse, type RegisterRequest } from '@dbview/shared';
import type { FastifyReply, FastifyRequest } from 'fastify';
import { AuthService } from './auth.service.js';
import type { AuthPrincipal } from './auth.types.js';
export declare class AuthController {
    private readonly auth;
    private readonly reflector;
    constructor(auth: AuthService, reflector: Reflector);
    login(body: LoginRequest, req: FastifyRequest, reply: FastifyReply): Promise<LoginResponse>;
    config(): AuthConfig;
    register(body: RegisterRequest, req: FastifyRequest, reply: FastifyReply): Promise<LoginResponse>;
    refresh(req: FastifyRequest, reply: FastifyReply): LoginResponse;
    logout(req: FastifyRequest, reply: FastifyReply): {
        ok: true;
    };
    me(principal: AuthPrincipal | undefined): MeResponse;
    changePassword(body: ChangePasswordRequest, principal: AuthPrincipal | undefined, req: FastifyRequest, reply: FastifyReply): Promise<LoginResponse>;
}
//# sourceMappingURL=auth.controller.d.ts.map