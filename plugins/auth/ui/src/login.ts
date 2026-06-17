/**
 * Shared auth *login UI* entry — split out from the main `@auth` barrel.
 *
 * These components carry visual deps (lucide-react icons, the auth stylesheet)
 * and a login wall. Keeping them out of `index.ts` lets plugins that only need
 * the auth *context* (`useAuth`, `AuthProvider`, the API) import from `@auth`
 * without dragging the login UI (and its transitive deps) into their bundle.
 *
 * Plugins that render the shared login wall import from `@auth/login`.
 */

export { default as LoginPage } from './components/LoginPage';
export { ProtectedRoute, useProtectedContent } from './components/ProtectedRoute';
