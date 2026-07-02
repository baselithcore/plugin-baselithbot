import { Body, Controller, Get, Post, Req, Res, UseGuards } from '@nestjs/common';
import { Reflector } from '@nestjs/core';
import {
  ChangePasswordRequestSchema,
  LoginRequestSchema,
  RegisterRequestSchema,
  type AuthConfig,
  type ChangePasswordRequest,
  type LoginRequest,
  type LoginResponse,
  type MeResponse,
  type RegisterRequest,
  type UserPublic,
} from '@dbview/shared';
import { UnauthorizedError } from '@dbview/shared';
import type { FastifyReply, FastifyRequest } from 'fastify';
import { ZodPipe } from '../common/zod.pipe.js';
import { Public } from '../common/public.decorator.js';
import { AllowPasswordChange } from '../common/password-change.decorator.js';
import { RateLimit, RateLimitGuard } from '../common/rate-limit.guard.js';
import { AuthService, refreshCookieTtl } from './auth.service.js';
import { CurrentUser } from './decorators.js';
import { isGatewayMode } from './gateway.js';
import { toPublicUser } from './auth.types.js';
import type { AuthPrincipal } from './auth.types.js';

const REFRESH_COOKIE = 'dbview_refresh';

function cookieOpts(maxAge?: number): Record<string, unknown> {
  return {
    httpOnly: true,
    secure: process.env.NODE_ENV === 'production',
    sameSite: 'strict' as const,
    path: '/api/auth',
    ...(maxAge !== undefined ? { maxAge } : {}),
  };
}

@Controller('auth')
export class AuthController {
  constructor(
    private readonly auth: AuthService,
    private readonly reflector: Reflector,
  ) {
    void this.reflector;
  }

  @Public()
  @UseGuards(RateLimitGuard)
  @RateLimit({ limit: 5, windowSec: 60 })
  @Post('login')
  async login(
    @Body(new ZodPipe(LoginRequestSchema)) body: LoginRequest,
    @Req() req: FastifyRequest,
    @Res({ passthrough: true }) reply: FastifyReply,
  ): Promise<LoginResponse> {
    const result = await this.auth.login(body.email, body.password, {
      ip: req.ip ?? null,
      userAgent: (req.headers['user-agent'] as string | undefined) ?? null,
    });
    reply.setCookie(REFRESH_COOKIE, result.refreshToken, cookieOpts(refreshCookieTtl));
    return {
      accessToken: result.accessToken,
      expiresIn: result.expiresIn,
      user: result.user,
    };
  }

  @Public()
  @Get('config')
  config(): AuthConfig {
    return {
      registrationEnabled: this.auth.isRegistrationEnabled(),
      gateway: isGatewayMode(),
    };
  }

  @Public()
  @UseGuards(RateLimitGuard)
  @RateLimit({ limit: 5, windowSec: 60 })
  @Post('register')
  async register(
    @Body(new ZodPipe(RegisterRequestSchema)) body: RegisterRequest,
    @Req() req: FastifyRequest,
    @Res({ passthrough: true }) reply: FastifyReply,
  ): Promise<LoginResponse> {
    const result = await this.auth.register(body, {
      ip: req.ip ?? null,
      userAgent: (req.headers['user-agent'] as string | undefined) ?? null,
    });
    reply.setCookie(REFRESH_COOKIE, result.refreshToken, cookieOpts(refreshCookieTtl));
    return {
      accessToken: result.accessToken,
      expiresIn: result.expiresIn,
      user: result.user,
    };
  }

  @Public()
  @UseGuards(RateLimitGuard)
  @RateLimit({ limit: 30, windowSec: 60 })
  @Post('refresh')
  refresh(
    @Req() req: FastifyRequest,
    @Res({ passthrough: true }) reply: FastifyReply,
  ): LoginResponse {
    const raw = readRefreshCookie(req);
    if (!raw) throw new UnauthorizedError('No refresh token present.');
    const result = this.auth.rotate(raw, {
      ip: req.ip ?? null,
      userAgent: (req.headers['user-agent'] as string | undefined) ?? null,
    });
    reply.setCookie(REFRESH_COOKIE, result.refreshToken, cookieOpts(refreshCookieTtl));
    return {
      accessToken: result.accessToken,
      expiresIn: result.expiresIn,
      user: result.user,
    };
  }

  @Public()
  @Post('logout')
  logout(
    @Req() req: FastifyRequest,
    @Res({ passthrough: true }) reply: FastifyReply,
  ): { ok: true } {
    const raw = readRefreshCookie(req);
    this.auth.logout(raw);
    reply.clearCookie(REFRESH_COOKIE, cookieOpts());
    return { ok: true };
  }

  @AllowPasswordChange()
  @Get('me')
  me(@CurrentUser() principal: AuthPrincipal | undefined): MeResponse {
    if (!principal) throw new UnauthorizedError();
    if (principal.source === 'api-key') {
      return {
        user: {
          id: principal.id,
          email: principal.email,
          displayName: 'Service Account',
          role: principal.role,
          isActive: true,
          createdAt: new Date(0).toISOString(),
          lastLoginAt: null,
          mustChangePassword: false,
        },
      };
    }
    const user = this.auth.getUser(principal.id);
    if (!user) throw new UnauthorizedError('User not found.');
    return { user: toPublicUser(user) };
  }

  @AllowPasswordChange()
  @Post('change-password')
  async changePassword(
    @Body(new ZodPipe(ChangePasswordRequestSchema)) body: ChangePasswordRequest,
    @CurrentUser() principal: AuthPrincipal | undefined,
    @Req() req: FastifyRequest,
    @Res({ passthrough: true }) reply: FastifyReply,
  ): Promise<LoginResponse> {
    if (!principal || principal.source !== 'jwt') {
      throw new UnauthorizedError('JWT session required.');
    }
    const updated: UserPublic = await this.auth.changePassword(
      principal.id,
      body.currentPassword,
      body.newPassword,
    );
    // Issue a fresh session so the access token reflects mustChangePassword=false
    // immediately. Refresh cookie is rotated to invalidate the prior token chain.
    const result = await this.auth.login(updated.email, body.newPassword, {
      ip: req.ip ?? null,
      userAgent: (req.headers['user-agent'] as string | undefined) ?? null,
    });
    reply.setCookie(REFRESH_COOKIE, result.refreshToken, cookieOpts(refreshCookieTtl));
    return {
      accessToken: result.accessToken,
      expiresIn: result.expiresIn,
      user: result.user,
    };
  }
}

function readRefreshCookie(req: FastifyRequest): string | null {
  const cookies = (req as FastifyRequest & { cookies?: Record<string, string | undefined> })
    .cookies;
  return cookies?.[REFRESH_COOKIE] ?? null;
}
