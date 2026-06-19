import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
// Resolve a path relative to this config file without Node typings (tsc -b
// type-checks this file and @types/node is not installed here).
const fromHere = (p) => new URL(p, import.meta.url).pathname;
export default defineConfig(({ command }) => ({
  plugins: [react()],
  base: command === 'build' ? '/baselithbot/ui/' : '/',
  resolve: {
    // Central auth context (shared single-source SSO). `@auth/login` MUST
    // precede `@auth` — first match wins.
    alias: [
      { find: '@auth/login', replacement: fromHere('../../auth/ui/src/login.ts') },
      { find: '@auth', replacement: fromHere('../../auth/ui/src/index.ts') },
    ],
  },
  build: {
    outDir: 'dist',
    emptyOutDir: true,
    sourcemap: false,
    chunkSizeWarningLimit: 900,
  },
  server: {
    port: 5180,
    open: '/',
    proxy: {
      '/baselithbot/dash': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
      '/baselithbot/run': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
      '/baselithbot/status': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
      '/baselithbot/metrics': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
      '/baselithbot/inbound': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
      '/baselithbot/ws': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
        ws: true,
      },
    },
  },
}));
