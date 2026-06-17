import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';
// Served from the plugin mount point; the API lives under /api/baselith_pitwall.
export default defineConfig({
  plugins: [react()],
  base: '/baselith_pitwall/',
  resolve: {
    alias: [
      // Map @auth imports to the shared central auth UI source (mirrors honeypot/cve_hunter).
      // The more specific `@auth/login` entry MUST precede `@auth` (first match wins).
      { find: '@auth/login', replacement: path.resolve(__dirname, '../../auth/ui/src/login.ts') },
      { find: '@auth', replacement: path.resolve(__dirname, '../../auth/ui/src/index.ts') },
    ],
  },
  build: { outDir: 'dist', emptyOutDir: true },
  server: {
    fs: {
      allow: ['..', '../../../auth/ui/src'],
    },
    proxy: {
      '/api/baselith_pitwall': 'http://localhost:8000',
    },
  },
});
