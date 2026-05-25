/**
 * `<Can>` — gating dichiarativo di UI per RBAC (Fase 7).
 *
 * UI gating ≠ autorizzazione: il backend resta la sorgente di verità.
 * Questo componente nasconde solo i bottoni/sezioni a cui l'utente non
 * può accedere — un attaccante che bypassa il render comunque sbatte
 * sul 403 lato server (`require_permission`).
 *
 * Esempi
 * ======
 *
 * ```tsx
 * // Singolo permesso
 * <Can perm="ingest.run"><Button onClick={ingest}>Ingest</Button></Can>
 *
 * // Multipli (OR)
 * <Can anyOf={["wiki.write", "wiki.delete"]}><EditToolbar/></Can>
 *
 * // Multipli (AND)
 * <Can allOf={["admin.user.manage", "admin.audit.read"]}><AdminPanel/></Can>
 *
 * // Ruolo invece di permesso
 * <Can role="editor"><EditorOnlyHint/></Can>
 *
 * // Fallback custom
 * <Can perm="feedback.delete" fallback={<DisabledButton/>}>
 *   <Button onClick={remove}>Delete</Button>
 * </Can>
 * ```
 */

import type { ReactNode } from 'react';

import { useAuth } from '../contexts/AuthContext';

interface CanProps {
  perm?: string;
  anyOf?: string[];
  allOf?: string[];
  role?: string;
  /** Render quando il check fallisce. Default: nulla. */
  fallback?: ReactNode;
  children: ReactNode;
}

export function Can({ perm, anyOf, allOf, role, fallback = null, children }: CanProps) {
  const { can, canAny, canAll, hasRole } = useAuth();

  // Almeno una condizione deve essere fornita — guard di programmazione.
  // Se nessuna è passata, default a "nascondi" per fail-closed UX.
  if (!perm && !anyOf?.length && !allOf?.length && !role) {
    return <>{fallback}</>;
  }

  if (perm && !can(perm)) return <>{fallback}</>;
  if (anyOf?.length && !canAny(anyOf)) return <>{fallback}</>;
  if (allOf?.length && !canAll(allOf)) return <>{fallback}</>;
  if (role && !hasRole(role)) return <>{fallback}</>;

  return <>{children}</>;
}

/**
 * Hook equivalente per logica condizionale che non si presta a JSX
 * (es. flag passato come prop, branching in event handler).
 */
export function usePermission(perm: string): boolean {
  const { can } = useAuth();
  return can(perm);
}
