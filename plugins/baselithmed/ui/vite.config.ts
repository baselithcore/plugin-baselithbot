import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';

export default defineConfig({
  plugins: [react()],
  base: '/static/baselithmed/',
  resolve: {
    alias: [
      // Map the shared central auth UI source into this plugin SPA.
      // The more specific `@auth/login` entry MUST precede `@auth` (first match wins).
      { find: '@auth/login', replacement: path.resolve(__dirname, '../../auth/ui/src/login.ts') },
      { find: '@auth', replacement: path.resolve(__dirname, '../../auth/ui/src/index.ts') },
    ],
  },
  build: {
    // Plugin serves from ui/dist (get_static_assets_path -> _STATIC_DIR).
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
    port: 5180,
    fs: {
      allow: ['..', '../../../auth/ui/src'],
    },
    proxy: {
      '/api/baselithmed': 'http://localhost:8000',
    },
  },
});
