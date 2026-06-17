import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';
// Relative base so built assets resolve under the plugin's `/ui/` mount,
// wherever the router prefix is mounted at runtime.
export default defineConfig({
  base: './',
  plugins: [react()],
  resolve: {
    alias: [
      // Map the shared central auth UI source so `@auth` resolves to the
      // sibling auth plugin (mirrors honeypot / cve_hunter).
      // The more specific `@auth/login` entry MUST precede `@auth` (first match wins).
      { find: '@auth/login', replacement: path.resolve(__dirname, '../../auth/ui/src/login.ts') },
      { find: '@auth', replacement: path.resolve(__dirname, '../../auth/ui/src/index.ts') },
    ],
  },
  server: {
    fs: {
      allow: ['..', '../../../auth/ui/src'],
    },
  },
  build: {
    // Plugin serves from ui/dist (see ui_static.py `_UI_DIST`).
    outDir: 'dist',
    emptyOutDir: true,
    chunkSizeWarningLimit: 1200,
  },
});
