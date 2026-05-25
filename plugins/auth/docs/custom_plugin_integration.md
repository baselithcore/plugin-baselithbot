# Guida all'Integrazione Auth per Plugin Custom

Questa guida spiega come proteggere i tuoi plugin custom (backend e frontend) utilizzando il sistema di autenticazione del framework.

## 1. Protezione Backend (FastAPI)

Tutti i router dei plugin devono essere protetti per evitare accessi non autorizzati alle API.

### File: `router.py`

Importa le dipendenze necessarie dal core e dal plugin auth:

```python
from fastapi import APIRouter, Depends
from core.auth import AuthRole
from plugins.auth.dependencies import require_roles
```

Applica la dipendenza di sicurezza al momento della creazione del `APIRouter`.
Raccomandiamo di permettere l'accesso sia agli amministratori (`ADMIN`) che agli utenti standard (`USER`).

```python
def create_router() -> APIRouter:
    router = APIRouter(
        prefix="/api/my_custom_plugin",
        tags=["my_custom_plugin"],
        # 🔒 PROTEZIONE QUI
        dependencies=[Depends(require_roles(AuthRole.ADMIN, AuthRole.USER))],
    )

    # ... definisci le tue rotte ...

    return router
```

> **Nota**: Se hai bisogno di rotte pubbliche, definiscile in un router separato senza dipendenze o usa `include_in_schema=False` se sono webhook interni.

---

## 2. Protezione Frontend (React Standalone App)

Se il tuo plugin ha una dashboard standalone (in `frontend/apps/il_tuo_plugin`), hai due opzioni:

### Opzione A: Usa AuthProvider (Raccomandato)

Utilizza il componente `AuthProvider` e `ProtectedRoute` dal modulo condiviso `@/auth`:

```tsx
// src/App.tsx
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { AuthProvider, ProtectedRoute, LoginPage } from '@/auth';
import MyPluginPanel from './components/MyPluginPanel';

const App = () => {
  return (
    <AuthProvider>
      <Router basename="/my_plugin">
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route
            path="/"
            element={
              <ProtectedRoute>
                <MyPluginPanel />
              </ProtectedRoute>
            }
          />
        </Routes>
      </Router>
    </AuthProvider>
  );
};

export default App;
```

### Opzione B: API Client con Auto-Refresh

Per le chiamate API, crea un client che gestisca automaticamente l'autenticazione:

```typescript
// src/components/api.ts
const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

function getAuthHeaders(): Record<string, string> {
  const token = sessionStorage.getItem('auth_access_token');
  return token ? { 'Authorization': `Bearer ${token}` } : {};
}

async function tryRefreshToken(): Promise<boolean> {
  try {
    const response = await fetch(`${API_BASE}/api/auth/refresh`, {
      method: 'POST',
      credentials: 'include',
    });
    if (!response.ok) return false;
    const data = await response.json();
    if (data.access_token) {
      sessionStorage.setItem('auth_access_token', data.access_token);
      return true;
    }
    return false;
  } catch { return false; }
}

function redirectToLogin(): void {
  const returnUrl = window.location.pathname + window.location.search;
  window.location.href = `/my_plugin/login?redirect=${encodeURIComponent(returnUrl)}`;
}

export async function apiFetch<T>(path: string, init?: RequestInit, isRetry = false): Promise<T> {
  const response = await fetch(`${API_BASE}/api/my_plugin${path}`, {
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
      ...getAuthHeaders(),
      ...(init?.headers || {}),
    },
    ...init,
  });

  // 401: Try refresh once, then redirect
  if (response.status === 401 && !isRetry) {
    if (await tryRefreshToken()) {
      return apiFetch<T>(path, init, true);
    }
    redirectToLogin();
    throw new Error('Authentication required');
  }

  // 403: Permission denied
  if (response.status === 403) {
    throw new Error('Access denied');
  }

  if (!response.ok) {
    throw new Error(await response.text() || 'API request failed');
  }
  return response.json();
}
```

## 3. Verifica

Dopo aver applicato le modifiche:

1. Riavvia i container: `docker-compose -f docker-compose.prod.yml up -d --build`
2. Accedi alla tua dashboard custom.
3. Dovresti essere reindirizzato automaticamente alla pagina di login.
4. Dopo il login, dovresti poter accedere alla dashboard.
5. Prova a chiamare le API del tuo plugin via curl/postman senza cookie: dovresti ricevere un errore `401 Unauthorized` o `403 Forbidden`.
