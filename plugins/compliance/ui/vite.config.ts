import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'node:path';

// Built artifacts are mounted at /compliance by the plugin, so assets must
// resolve under that base. The dev server proxies the compliance API to the
// local backend so `npm run dev` works without a separate gateway.
export default defineConfig({
  base: process.env.VITE_BASE_PATH || '/compliance/',
  plugins: [react()],
  resolve: {
    // Central auth context (shared single-source SSO). `@auth/login` and
    // `@auth` MUST precede `@` — array order is first-match-wins.
    alias: [
      { find: '@auth/login', replacement: path.resolve(__dirname, '../../auth/ui/src/login.ts') },
      { find: '@auth', replacement: path.resolve(__dirname, '../../auth/ui/src/index.ts') },
      { find: '@', replacement: path.resolve(__dirname, './src') },
    ],
  },
  build: { outDir: 'dist', emptyOutDir: true },
  server: {
    port: 5182,
    proxy: {
      '/api/compliance': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
});
