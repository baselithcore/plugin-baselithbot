import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  base: '/red-agent/ui/',
  build: {
    outDir: 'dist',
    sourcemap: true,
    target: 'es2022',
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (!id.includes('node_modules')) return undefined;
          if (id.includes('react') || id.includes('react-router-dom')) return 'vendor-react';
          if (
            id.includes('three') ||
            id.includes('3d-force-graph') ||
            id.includes('three-spritetext') ||
            id.includes('d3-')
          ) {
            return 'vendor-graph3d';
          }
          if (id.includes('cytoscape')) return 'vendor-cytoscape';
          if (id.includes('echarts')) return 'vendor-charts';
          if (id.includes('marked') || id.includes('dompurify')) return 'vendor-markdown';
          return undefined;
        },
      },
    },
  },
  server: {
    port: 5273,
    open: '/red-agent/ui/',
    proxy: {
      // Forward backend routes but NOT the UI base (/red-agent/ui) — vite owns those.
      '^/red-agent/(?!ui($|/)).*': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        ws: true,
        configure: (proxy) => {
          // Backend CSRF middleware rejects state-changing requests whose
          // Origin is not in ALLOW_ORIGINS. The vite dev server runs on
          // :5273 which production deployments don't whitelist, so we
          // rewrite Origin/Referer to localhost:8000 (always allowed).
          proxy.on('proxyReq', (proxyReq) => {
            proxyReq.setHeader('origin', 'http://localhost:8000');
            proxyReq.setHeader('referer', 'http://localhost:8000/');
          });
        },
      },
    },
  },
});
