import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  // Standalone builds keep the default root base; embedded (plugin) builds
  // set VITE_BASE_PATH (e.g. '/dbview/') so assets resolve under the mount.
  base: process.env.VITE_BASE_PATH ?? '/',
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
