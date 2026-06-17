import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';
import path from 'node:path';

// Built artifacts are mounted at /baselithcontrol by the plugin, so assets must
// resolve under that base. The dev server proxies the control API to the local
// backend so `npm run dev` works without a separate gateway.
export default defineConfig({
  base: process.env.VITE_BASE_PATH || '/baselithcontrol/',
  plugins: [react(), tailwindcss()],
  resolve: { alias: { '@': path.resolve(__dirname, './src') } },
  build: { outDir: 'dist', emptyOutDir: true },
  server: {
    port: 5181,
    proxy: {
      '/api/baselithcontrol': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
});
