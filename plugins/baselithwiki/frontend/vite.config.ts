import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';
import path from 'node:path';

// Multi-entry build:
// - ``main``: SPA principale (index.html alla root).
// - ``embed``: mini-app chat caricato dentro iframe del widget
//   (frontend/embed/index.html). Output in ``dist/embed/``.
// - Widget loader vanilla TS (``frontend/embed-loader/widget.ts``) ha un
//   build dedicato — vedi ``vite.widget.config.ts``. Bundle distinto
//   per evitare che il loader trascini React/Tailwind dentro lo
//   script-tag eseguito sul sito ospitante.
export default defineConfig({
  // Base public path. Default '/' reproduces upstream standalone behaviour;
  // the BaselithCore plugin build sets VITE_BASE_PATH=/baselithwiki/ so the
  // compiled asset URLs resolve under the mount point.
  base: process.env.VITE_BASE_PATH || '/',
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: { '@': path.resolve(__dirname, './src') },
  },
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
      // Auth endpoints (Fase 6): refresh cookie httpOnly path=/auth, login/me/logout.
      '/auth': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
  build: {
    rollupOptions: {
      input: {
        main: path.resolve(__dirname, 'index.html'),
        embed: path.resolve(__dirname, 'embed/index.html'),
      },
      output: {
        manualChunks: {
          motion: ['framer-motion'],
          markdown: ['react-markdown', 'remark-gfm', 'rehype-highlight', 'highlight.js'],
          icons: ['lucide-react'],
          toast: ['sonner'],
        },
      },
    },
  },
});
