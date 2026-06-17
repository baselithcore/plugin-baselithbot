/// <reference types="vite/client" />
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = dirname(fileURLToPath(import.meta.url));

export default defineConfig({
  base: '/auth/',
  plugins: [react()],
  resolve: {
    alias: {
      '@': resolve(__dirname, '../../src'),
    },
  },
  build: {
    // The plugin serves built assets from ../static (see
    // AuthPlugin.get_static_assets_path). Emit there directly so a build is
    // immediately live — no manual dist -> static copy step.
    outDir: '../static',
    emptyOutDir: true,
  },
  server: {
    port: 5175,
    host: true,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
});
