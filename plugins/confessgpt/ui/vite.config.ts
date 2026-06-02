import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// SPA is mounted at /confessgpt/ by the core lifespan helper
// (see core/api/lifespan.py:_mount_plugin_static). Setting Vite
// base to match means generated asset paths resolve correctly
// when served by StaticFiles(html=True).
export default defineConfig({
  plugins: [react()],
  base: '/confessgpt/',
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
    proxy: {
      '/api/confessgpt': 'http://localhost:8000',
    },
  },
});
