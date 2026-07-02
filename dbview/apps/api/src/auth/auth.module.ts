import { Module } from '@nestjs/common';
import { AuthService } from './auth.service.js';
import { AuthController } from './auth.controller.js';
import { UsersController } from './users.controller.js';
import { JwtAuthGuard } from './jwt-auth.guard.js';
import { RolesGuard } from './roles.guard.js';
import { RateLimitGuard } from '../common/rate-limit.guard.js';

@Module({
  controllers: [AuthController, UsersController],
  providers: [AuthService, JwtAuthGuard, RolesGuard, RateLimitGuard],
  exports: [AuthService, JwtAuthGuard, RolesGuard],
})
export class AuthModule {}
