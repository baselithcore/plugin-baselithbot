#!/usr/bin/env node
/**
 * Build-time guard: the control-plane UI compiles the `auth` plugin's shared
 * source via the `@auth` / `@auth/login` aliases (../../auth/ui/src). Node
 * resolves auth's transitive deps (e.g. `qrcode`, used by the shared MFA
 * `QrCode` component) from auth's OWN node_modules — never from this package's —
 * so building here requires auth's UI deps to be installed first.
 *
 * This makes `npm run build` self-sufficient on a fresh checkout instead of
 * failing with `TS2307: Cannot find module 'qrcode'`. It installs auth's deps
 * only when they are actually missing, so warm builds pay nothing.
 */
import { execFileSync } from 'node:child_process';
import { existsSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const here = dirname(fileURLToPath(import.meta.url));
const authUi = resolve(here, '../../../auth/ui');

// Layouts without the sibling auth plugin (e.g. a standalone export) build
// against vendored sources — nothing to install, so skip silently.
if (!existsSync(authUi)) process.exit(0);

// `qrcode` is the canary: present ⇒ auth's deps are installed.
if (existsSync(resolve(authUi, 'node_modules/qrcode/package.json'))) process.exit(0);

// Static, non-interpolated args — no shell, so no command-injection surface.
const subcommand = existsSync(resolve(authUi, 'package-lock.json')) ? 'ci' : 'install';
const npm = process.platform === 'win32' ? 'npm.cmd' : 'npm';
console.log(`[prebuild] auth UI deps missing — running \`npm ${subcommand}\` in ${authUi}`);
execFileSync(npm, [subcommand, '--no-audit', '--no-fund'], { cwd: authUi, stdio: 'inherit' });
