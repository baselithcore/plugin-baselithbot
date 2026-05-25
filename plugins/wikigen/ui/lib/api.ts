// Barrel: l'API client è splittato in moduli per dominio sotto lib/api/.
// Mantieni questo file come unico punto di import per i consumer ('../lib/api').
export { ApiError, BASE } from './api/client';
export {
  postFormWithProgress,
  runWithConcurrency,
  type UploadOptions,
  type UploadProgress,
} from './api/_upload';
export * from './api/wiki';
export * from './api/chat';
export * from './api/ingest';
export * from './api/feedback';
export * from './api/admin';
