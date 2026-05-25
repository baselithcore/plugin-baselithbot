import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// ``VITE_BASE_PATH`` lets host integrations (e.g. the baselithcore plugin
// reverse-proxy that serves the SPA at ``/dbview/``) rewrite asset URLs at
// build time. Unset = root mount, identical to the upstream standalone
// behaviour.
const basePath = process.env.VITE_BASE_PATH ?? '/';

export default defineConfig({
  base: basePath,
  plugins: [react()],
  resolve: {
    // Avoid duplicate three.js instances when the app and react-force-graph-3d
    // resolve different versions; ForceGraph silently drops custom Three objects
    // that come from a different module instance.
    dedupe: ['three'],
  },
  server: {
    host: true,
    port: 5173,
    proxy: {
      '/api': {
        target: process.env.VITE_API_URL ?? 'http://localhost:3001',
        changeOrigin: true,
      },
    },
  },
  build: {
    // Heavy graph libs end up in dedicated chunks so the initial paint
    // doesn't ship them. Lazy routes (ResultGraph2D/3D) load them on demand.
    chunkSizeWarningLimit: 800,
    rollupOptions: {
      output: {
        manualChunks: {
          'graph-3d': ['three', 'three-spritetext', 'react-force-graph-3d'],
          'graph-2d': ['react-force-graph-2d'],
          xyflow: ['@xyflow/react', '@dagrejs/dagre'],
          radix: [
            '@radix-ui/react-dialog',
            '@radix-ui/react-popover',
            '@radix-ui/react-switch',
            '@radix-ui/react-tabs',
            '@radix-ui/react-tooltip',
          ],
          motion: ['framer-motion'],
        },
      },
    },
  },
});
