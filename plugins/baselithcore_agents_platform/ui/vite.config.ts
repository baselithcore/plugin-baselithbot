import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';

// The dashboard is served by the plugin router under this sub-path, so the
// build must emit asset URLs relative to it.
export default defineConfig({
  base: '/api/baselithcore_agents_platform/ui/',
  plugins: [react()],
  resolve: {
    alias: [
      // Map the shared central auth UI source (relative from this ui dir:
      // ui -> baselithcore_agents_platform -> plugins/ -> auth/ui/src).
      // The more specific `@auth/login` entry MUST precede `@auth` (first match wins).
      { find: '@auth/login', replacement: path.resolve(__dirname, '../../auth/ui/src/login.ts') },
      { find: '@auth', replacement: path.resolve(__dirname, '../../auth/ui/src/index.ts') },
    ],
  },
  build: {
    // Plugin serves from ui/dist (see ui_static._UI_DIST) — keep emitting there.
    outDir: 'dist',
    emptyOutDir: true,
    sourcemap: false,
  },
  server: {
    fs: {
      allow: ['..', '../../auth/ui/src'],
    },
    proxy: {
      '/api/baselithcore_agents_platform': 'http://localhost:8000',
    },
  },
});
