import { defineConfig } from 'vite';
import path from 'node:path';

// Vite library mode dedicato al widget loader (``embed-loader/widget.ts``).
//
// Output: ``dist/embed.js`` — singolo file IIFE servibile via
// ``<script src="…/embed.js">`` sul sito ospitante. NO React, NO
// Tailwind, NO altre dep — solo vanilla TS compilato.
//
// Separato dal build principale per:
// - non polluire i chunk dello SPA con la logica del widget.
// - evitare che ``manualChunks`` spezzetti il loader in più file
//   (lo script tag carica UN url, basta).
// - rendere il deploy dello snippet stabile (URL fisso /embed.js).
//
// Build: ``npm run build:widget``. Il main build (``npm run build``)
// continua a usare vite.config.ts senza vedere questo file.
export default defineConfig({
  build: {
    outDir: 'dist',
    emptyOutDir: false,
    lib: {
      entry: path.resolve(__dirname, 'embed-loader/widget.ts'),
      name: 'WikiEmbedWidget',
      formats: ['iife'],
      fileName: () => 'embed.js',
    },
    rollupOptions: {
      output: {
        // No global export — il widget esegue init() come side-effect.
        extend: false,
        inlineDynamicImports: true,
      },
    },
    minify: 'esbuild',
    target: 'es2018',
    sourcemap: false,
  },
});
