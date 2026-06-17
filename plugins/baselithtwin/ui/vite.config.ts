import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { fileURLToPath } from 'node:url';

// Resolve sibling-plugin paths without depending on @types/node globals.
const authEntry = fileURLToPath(new URL('../../auth/ui/src/index.ts', import.meta.url));
const authLoginEntry = fileURLToPath(new URL('../../auth/ui/src/login.ts', import.meta.url));

// The dashboard is served by the plugin router under /api/baselithtwin/ui/,
// so assets must resolve relative to that base rather than the domain root.
export default defineConfig({
  plugins: [react()],
  base: '/api/baselithtwin/ui/',
  resolve: {
    alias: [
      // Map the shared central auth UI source for `@auth` imports.
      // The more specific `@auth/login` entry MUST precede `@auth` (first match wins).
      { find: '@auth/login', replacement: authLoginEntry },
      { find: '@auth', replacement: authEntry },
    ],
  },
  server: {
    fs: {
      allow: ['..', '../../../auth/ui/src'],
    },
  },
  build: { outDir: 'dist', emptyOutDir: true, sourcemap: false },
});
