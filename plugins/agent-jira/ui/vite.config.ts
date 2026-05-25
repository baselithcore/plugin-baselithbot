import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = dirname(fileURLToPath(import.meta.url));

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  envDir: '..',
  resolve: {
    alias: {
      '@': resolve(__dirname, './src'),
    },
  },
  build: {
    outDir: '../app/static/frontend',
    emptyOutDir: true,
    chunkSizeWarningLimit: 700,
    rollupOptions: {
      output: {
        manualChunks: (id) => {
          if (id.includes('node_modules')) {
            if (id.includes('react') || id.includes('scheduler')) return 'react-vendor';
            if (id.includes('remark') || id.includes('rehype') || id.includes('mdast'))
              return 'markdown';
            if (id.includes('lucide-react')) return 'icons';
            return 'vendor';
          }
        },
      },
    },
  },
  server: {
    port: 5173,
    host: true,
  },
});
