# Module: api

FastAPI router composito. Tutti endpoint sotto `/api/v1`.

## Submodules

| File | Responsabilità |
|------|----------------|
| [routes.py](../../docheck-engine/src/docheck/api/routes.py) | Health, pubkey, documents upload/analyze, WS streaming |
| [auth.py](../../docheck-engine/src/docheck/api/auth.py) | Login, /me |
| [policies.py](../../docheck-engine/src/docheck/api/policies.py) | List policies + rules |
| [audit.py](../../docheck-engine/src/docheck/api/audit.py) | Audit log read + chain integrity |
| [deps.py](../../docheck-engine/src/docheck/api/deps.py) | `current_principal` + `require(resource, action)` |

## RBAC mapping

| Endpoint | Permission |
|----------|-----------|
| POST /documents | `document:write` |
| POST /documents/{id}/analyze | `document:read` |
| GET /policies | `policy:read` |
| GET /policies/{id}/rules | `policy:read` |
| GET /audit/log | `audit:read` |
| GET /audit/verify | `audit:read` |
| WS /ws/analysis/{id} | (no enforce — TODO MVP late) |

## Aggiungere endpoint

1. Submodule sotto `api/<topic>.py` con `router = APIRouter()`.
2. Dependency `Depends(require(resource, action))` per RBAC.
3. Audit append per azioni stato-changing (upload/create/delete).
4. Registra in [`api/__init__.py`](../../docheck-engine/src/docheck/api/__init__.py).
5. Doc in [`docs/api/endpoints.md`](../api/endpoints.md).
