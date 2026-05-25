import { Controller, Get, HttpException } from '@nestjs/common';
import { existsSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { accessSync, constants } from 'node:fs';
import { Public } from '../common/public.decorator.js';

interface DependencyResult {
  name: string;
  required: boolean;
  ready: boolean;
  status: 'ok' | 'error' | 'disabled';
  error?: string;
}

interface ReadyResponse {
  status: 'ok' | 'degraded';
  ready: boolean;
  uptime: number;
  version: string;
  dependencies: Record<string, DependencyResult>;
}

@Controller('health')
@Public()
export class HealthController {
  @Get()
  health(): { status: 'ok'; uptime: number; version: string } {
    return {
      status: 'ok',
      uptime: Math.round(process.uptime()),
      version: process.env.APP_VERSION ?? '0.1.0',
    };
  }

  @Get('live')
  live(): { status: 'alive' } {
    return { status: 'alive' };
  }

  @Get('ready')
  ready(): ReadyResponse {
    const dependencies: Record<string, DependencyResult> = {
      dataDir: this.checkDataDir(),
      jwtSecret: this.checkJwtSecret(),
      encryptionSecret: this.checkEncryptionSecret(),
    };

    const blocking = Object.values(dependencies).filter((d) => d.required && !d.ready);
    const status = blocking.length === 0 ? 'ok' : 'degraded';
    const ready = blocking.length === 0;
    const body: ReadyResponse = {
      status,
      ready,
      uptime: Math.round(process.uptime()),
      version: process.env.APP_VERSION ?? '0.1.0',
      dependencies,
    };
    if (!ready) throw new HttpException(body, 503);
    return body;
  }

  private checkDataDir(): DependencyResult {
    const path = resolve(process.env.DBVIEW_DATA_DIR ?? './data');
    try {
      const probe = existsSync(path) ? path : dirname(path);
      accessSync(probe, constants.W_OK);
      return { name: 'dataDir', required: true, ready: true, status: 'ok' };
    } catch (err) {
      return {
        name: 'dataDir',
        required: true,
        ready: false,
        status: 'error',
        error: (err as Error).message,
      };
    }
  }

  private checkJwtSecret(): DependencyResult {
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

  private checkEncryptionSecret(): DependencyResult {
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
}
