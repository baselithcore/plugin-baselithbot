# Guida all'Integrazione Auth nei Plugin

Questa guida spiega come proteggere le rotte e i componenti dei tuoi plugin personalizzati utilizzando il sistema di autenticazione centralizzato.

## 🏗️ Architettura & Deployment (VPS + Docker)

Poiché il framework gira su Docker, è fondamentale che tutti i servizi condividano correttamente le configurazioni di rete e sicurezza.

### Configurazione Docker

Se il tuo plugin richiede un container separato (es. un microservizio database o worker) e deve essere esposto pubblicamente:

1. **Rete Proxy**: Assicurati che il container sia collegato alla rete `proxy` (o quella configurata per Traefik/Reverse Proxy) se deve ricevere traffico dall'esterno.
2. **Variabili d'Ambiente**: Per validare i token JWT internamente (se necessario), il container deve avere le stesse variabili critiche del core, in particolare:
    * `SECRET_KEY` (Deve corrispondere esattamente a quella in `.env.prod`)
    * `AUTH_ALGORITHM` (Default: HS256)

Esempio `docker-compose.plugin.yml`:

```yaml
services:
  my-plugin:
    image: my-plugin-image
    networks:
      - proxy  # Rete pubblica per ingress
      - ai_net # Rete interna per comunicare con Core/Auth
    environment:
      - SECRET_KEY=${SECRET_KEY}

### 🌐 Configurazione Nginx Proxy Manager (NPM)

Se usi **Nginx Proxy Manager** per gestire i domini e SSL, segui questi passaggi per esporre correttamente il framework.

#### 1. Preparazione Rete Docker
Assicurati che il container `baselith-core-frontend` sia collegato alla stessa rete di NPM (es. `proxy`).
Modifica `docker-compose.prod.yml`:

```yaml
services:
  frontend:
    # ...
    networks:
      - ai_net
      - proxy  # <--- Aggiungi questa

networks:
  # ...
  proxy:
    external: true
```

#### 2. Configurazione Proxy Host (UI)

Nel pannello di NPM, crea un nuovo **Proxy Host**:

* **Details**:
    * **Domain Names**: `dashboard.tuodominio.com`
    * **Scheme**: `http`
    * **Forward Hostname**: `baselith-core-frontend`
    * **Forward Port**: `80`
    * **Cache Assets**: Disabilitato (consigliato per dev/dashboard dinamiche)
    * **Websockets Support**: **ABILITATO** (Cruciale per il Live Feed/Socket.IO)

* **SSL**:
    * **Force SSL**: Abilitato
    * **HSTS Enabled**: Abilitato

* **Advanced**:
    Se riscontri problemi con i rate limiter o gli IP, aggiungi questa configurazione per passare correttamente l'IP reale:

```nginx
proxy_set_header X-Real-IP $remote_addr;
proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
proxy_set_header X-Forwarded-Proto $scheme;
```

---

## 🐍 Integrazione Backend (Python/FastAPI)

Il metodo standard per proteggere le API del tuo plugin è usare le **Dependencies** FastAPI fornite da `plugins.auth`.

### 1. Importare le Dipendenze

```python
from fastapi import APIRouter, Depends
from core.auth.types import AuthRole
from plugins.auth.dependencies import (
    get_current_active_user,  # Richiede solo login
    require_role,             # Richiede ruolo specifico
    require_admin             # Shortcut per ruolo ADMIN
)
```

### 2. Proteggere le Rotte

**Protezione Base (Solo utente loggato):**

```python
@router.get("/my-plugin/data")
async def get_data(user = Depends(get_current_active_user)):
    return {"message": f"Hello {user.email}"}
```

**Protezione per Ruolo (RBAC):**

```python
@router.post("/my-plugin/admin-action")
async def sensitive_action(
    user = Depends(require_role(AuthRole.ADMIN, AuthRole.SERVICE))
):
    # Eseguito solo se user è admin o service
    return {"status": "executed"}
```

**Protezione Intero Router:**
Puoi proteggere tutte le rotte di un plugin in un colpo solo:

```python
router = APIRouter(
    prefix="/api/my-plugin",
    dependencies=[Depends(require_role(AuthRole.ADMIN))]
)
```

---

## ⚛️ Integrazione Frontend (React)

Per integrare l'autenticazione nella UI del tuo plugin dashboard.

### 1. Proteggere le Rotte (React Router)

Nel file principale del tuo plugin (es. `App.tsx` o configurazione rotte):

```tsx
import { ProtectedRoute } from '@/auth/ProtectedRoute';

<Route 
  path="/my-plugin" 
  element={
    <ProtectedRoute requiredRole="user">
       <MyPluginDashboard />
    </ProtectedRoute>
  } 
/>
```

### 2. Accedere ai Dati Utente (Hook)

Per mostrare contenuti dinamici in base all'utente:

```tsx
import { useAuth } from '@/auth/AuthContext';

export const MyComponent = () => {
  const { user, hasRole, canAccessTab } = useAuth();

  if (hasRole('admin')) {
    return <AdminControls />;
  }

  return <div>Welcome {user?.email}</div>;
};
```

### 3. Chiamate API Autenticate

Usa il client `authApi` o assicurati di passare le credenziali (cookie) nelle richieste `fetch`/`axios`:

```ts
// Le richieste verso /api/* includono automaticamente 
// i cookie HttpOnly se configurato "credentials: include"
const response = await fetch('/api/my-plugin/data');
```

---

## 🛡️ Best Practices per Plugin

1. **Least Privilege**: Richiedi sempre il ruolo minimo necessario (es. `user` o `guest`) invece di `admin`.
2. **API Keys**: Se il tuo plugin deve essere chiamato da script esterni, considera di implementare un meccanismo di API Key separato o usa un utente di servizio con ruolo `JOB`.
3. **Audit**: Logga le azioni sensibili includendo `user.email` (sanitizzato) nei log.
