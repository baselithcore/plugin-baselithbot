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
    // Single React instance. ``@auth`` is path-aliased to the auth plugin's
    // SOURCE, which carries its own React 18 in ``auth/ui/node_modules`` while
    // this UI ships React 19 — without dedupe both get bundled and the auth
    // components hit a null hook dispatcher ("Cannot read properties of null
    // (reading 'useState')"). Force every ``react``/``react-dom`` import to
    // resolve to this UI's copy so the whole bundle shares one React.
    dedupe: ['react', 'react-dom'],
    // Shared central-auth UI. ``@auth/login`` MUST precede ``@auth`` — the
    // resolver stops at the first match (same pattern as baselithbot/red_agent).
    // Path-aliased to the auth plugin's SOURCE; its transitive deps (lucide,
    // qrcode, react-i18next) resolve from ``plugins/auth/ui/node_modules`` at
    // build time, so install those before building this UI.
    alias: [
      { find: '@auth/login', replacement: path.resolve(__dirname, '../../auth/ui/src/login.ts') },
      { find: '@auth', replacement: path.resolve(__dirname, '../../auth/ui/src/index.ts') },
      { find: '@', replacement: path.resolve(__dirname, './src') },
    ],
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
