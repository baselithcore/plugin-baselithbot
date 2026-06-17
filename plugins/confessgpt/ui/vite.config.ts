import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'node:path';

// SPA is mounted at /confessgpt/ by the core lifespan helper
// (see core/api/lifespan.py:_mount_plugin_static). Setting Vite
// base to match means generated asset paths resolve correctly
// when served by StaticFiles(html=True).
export default defineConfig({
  plugins: [react()],
  base: '/confessgpt/',
  resolve: {
    alias: [
      // Map auth/src relative imports to the correct auth UI source directory.
      // The more specific `@auth/login` entry MUST precede `@auth` (first match wins).
      { find: '@auth/login', replacement: path.resolve(__dirname, '../../auth/ui/src/login.ts') },
      { find: '@auth', replacement: path.resolve(__dirname, '../../auth/ui/src/index.ts') },
    ],
  },
  build: {
    outDir: 'dist',
    emptyOutDir: true,
    sourcemap: false,
    rollupOptions: {
      output: {
        manualChunks: {
          vendor: ['react', 'react-dom'],
          motion: ['framer-motion'],
        },
      },
    },
  },
  server: {
    port: 5181,
    fs: {
      allow: ['..', '../../auth/ui/src', '../../../auth/ui/src'],
    },
    proxy: {
      '/api/confessgpt': 'http://localhost:8000',
    },
  },
});
