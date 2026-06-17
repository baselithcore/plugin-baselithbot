import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';
import path from 'node:path';

// Base public path. Standalone dev defaults to '/'; the BaselithCore plugin
// build sets VITE_BASE_PATH=/baselithbrain/ so compiled asset URLs resolve
// under the mount point. The API client derives its base from the same value.
export default defineConfig({
  base: process.env.VITE_BASE_PATH || '/',
  plugins: [react(), tailwindcss()],
  resolve: {
    // `@auth` pulls source from ../../auth/ui/src, whose bare `react` imports
    // would otherwise resolve to auth/ui/node_modules → a 2nd React copy →
    // null dispatcher ("Cannot read properties of null (reading 'useState')").
    // Force a single instance from this package.
    dedupe: ['react', 'react-dom', 'react/jsx-runtime'],
    // Shared central auth UI source (mirrors honeypot/cve_hunter). Array form
    // with the more-specific `@auth/login` entry first (first match wins);
    // `@` stays last so the @auth finds are matched before it.
    alias: [
      { find: '@auth/login', replacement: path.resolve(__dirname, '../../auth/ui/src/login.ts') },
      { find: '@auth', replacement: path.resolve(__dirname, '../../auth/ui/src/index.ts') },
      { find: '@', replacement: path.resolve(__dirname, './src') },
    ],
  },
  server: {
    port: 5174,
    fs: { allow: ['..', '../../../auth/ui/src'] },
    proxy: { '/api': { target: 'http://127.0.0.1:8000', changeOrigin: true } },
  },
  build: {
    outDir: 'dist',
    rollupOptions: {
      output: {
        manualChunks: {
          tiptap: ['@tiptap/core', '@tiptap/react', '@tiptap/starter-kit', 'tiptap-markdown'],
          graph2d: ['react-force-graph-2d'],
          graph3d: ['react-force-graph-3d', 'three', 'three-spritetext'],
          markdown: ['react-markdown', 'remark-gfm'],
          icons: ['lucide-react'],
        },
      },
    },
  },
});
