/// <reference types="vite/client" />
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = dirname(fileURLToPath(import.meta.url));

export default defineConfig({
  base: '/cve_hunter/',
  plugins: [react()],
  resolve: {
    alias: [
      { find: '@', replacement: resolve(__dirname, '../../src') },
      // Map auth/src relative imports to the correct auth UI source directory.
      // The more specific `@auth/login` entry MUST precede `@auth` (first match wins).
      { find: '@auth/login', replacement: resolve(__dirname, '../../auth/ui/src/login.ts') },
      { find: '@auth', replacement: resolve(__dirname, '../../auth/ui/src/index.ts') },
    ],
  },
  build: {
    // Plugin serves from ../static (get_static_assets_path) — emit there.
    outDir: '../static',
    emptyOutDir: true,
  },
  server: {
    port: 5174,
    host: true,
    fs: {
      allow: ['..', '../../auth/ui/src'],
    },
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
});
