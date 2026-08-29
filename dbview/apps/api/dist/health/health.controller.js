var __decorate = (this && this.__decorate) || function (decorators, target, key, desc) {
    var c = arguments.length, r = c < 3 ? target : desc === null ? desc = Object.getOwnPropertyDescriptor(target, key) : desc, d;
    if (typeof Reflect === "object" && typeof Reflect.decorate === "function") r = Reflect.decorate(decorators, target, key, desc);
    else for (var i = decorators.length - 1; i >= 0; i--) if (d = decorators[i]) r = (c < 3 ? d(r) : c > 3 ? d(target, key, r) : d(target, key)) || r;
    return c > 3 && r && Object.defineProperty(target, key, r), r;
};
var __metadata = (this && this.__metadata) || function (k, v) {
    if (typeof Reflect === "object" && typeof Reflect.metadata === "function") return Reflect.metadata(k, v);
};
import { Controller, Get, HttpException } from '@nestjs/common';
import { existsSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { accessSync, constants } from 'node:fs';
import { Public } from '../common/public.decorator.js';
let HealthController = class HealthController {
    health() {
        return {
            status: 'ok',
            uptime: Math.round(process.uptime()),
            version: process.env.APP_VERSION ?? '0.1.0',
        };
    }
    live() {
        return { status: 'alive' };
    }
    ready() {
        const dependencies = {
            dataDir: this.checkDataDir(),
            jwtSecret: this.checkJwtSecret(),
            encryptionSecret: this.checkEncryptionSecret(),
        };
        const blocking = Object.values(dependencies).filter((d) => d.required && !d.ready);
        const status = blocking.length === 0 ? 'ok' : 'degraded';
        const ready = blocking.length === 0;
        const body = {
            status,
            ready,
            uptime: Math.round(process.uptime()),
            version: process.env.APP_VERSION ?? '0.1.0',
            dependencies,
        };
        if (!ready)
            throw new HttpException(body, 503);
        return body;
    }
    checkDataDir() {
        const path = resolve(process.env.DBVIEW_DATA_DIR ?? './data');
        try {
            const probe = existsSync(path) ? path : dirname(path);
            accessSync(probe, constants.W_OK);
            return { name: 'dataDir', required: true, ready: true, status: 'ok' };
        }
        catch (err) {
            return {
                name: 'dataDir',
                required: true,
                ready: false,
                status: 'error',
                error: err.message,
            };
        }
    }
    checkJwtSecret() {
        const s = process.env.DBVIEW_JWT_SECRET ?? '';
        if (s.length >= 32) {
            return { name: 'jwtSecret', required: true, ready: true, status: 'ok' };
        }
        return {
            name: 'jwtSecret',
            required: true,
            ready: false,
            status: 'error',
            error: 'DBVIEW_JWT_SECRET missing or too short.',
        };
    }
    checkEncryptionSecret() {
        const s = process.env.DBVIEW_SECRET ?? '';
        if (s.length >= 16) {
            return { name: 'encryptionSecret', required: true, ready: true, status: 'ok' };
        }
        return {
            name: 'encryptionSecret',
            required: true,
            ready: false,
            status: 'error',
            error: 'DBVIEW_SECRET missing or too short.',
        };
    }
};
__decorate([
    Get(),
    __metadata("design:type", Function),
    __metadata("design:paramtypes", []),
    __metadata("design:returntype", Object)
], HealthController.prototype, "health", null);
__decorate([
    Get('live'),
    __metadata("design:type", Function),
    __metadata("design:paramtypes", []),
    __metadata("design:returntype", Object)
], HealthController.prototype, "live", null);
__decorate([
    Get('ready'),
    __metadata("design:type", Function),
    __metadata("design:paramtypes", []),
    __metadata("design:returntype", Object)
], HealthController.prototype, "ready", null);
HealthController = __decorate([
    Controller('health'),
    Public()
], HealthController);
export { HealthController };
//# sourceMappingURL=health.controller.js.map