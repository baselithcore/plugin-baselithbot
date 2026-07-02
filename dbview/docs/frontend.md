# Frontend

Vite + React 19 + Tailwind + React Flow + TanStack Query + Zustand. Three-pane resizable workspace.

## Panel map

| Panel             | File                  | Role                                                                          |
| ----------------- | --------------------- | ----------------------------------------------------------------------------- |
| `TopBar`          | `TopBar.tsx`          | Connection switcher, theme toggle, command-palette trigger, settings, logout. |
| `ConnectionPanel` | `ConnectionPanel.tsx` | Sidebar list of connections, create/test/delete, dump upload.                 |
| `HistoryPanel`    | `HistoryPanel.tsx`    | Recent NL questions with favorite/delete.                                     |
| `GraphViewport`   | `GraphViewport.tsx`   | React Flow canvas, schema graph, 2D/3D toggle.                                |
| `NL2QueryPanel`   | `NL2QueryPanel.tsx`   | NL prompt textarea, provider/model selector, conversation history.            |
| `ResultTable`     | `ResultTable.tsx`     | Sortable result table with CSV export.                                        |
| `DetailDrawer`    | `DetailDrawer.tsx`    | Right-side details for selected table/column/entity.                          |
| `CommandPalette`  | `CommandPalette.tsx`  | `cmdk` fuzzy search; ⌘K.                                                      |
| `StatusBar`       | `StatusBar.tsx`       | Bottom: row count, duration, warnings.                                        |
| `SettingsDialog`  | `SettingsDialog.tsx`  | Theme, LLM provider, Ollama URL, response locale.                             |
| `LoginPage`       | `LoginPage.tsx`       | Email + password auth. Reads `/api/auth/config` to show signup if enabled.    |

All under [apps/web/src/](../apps/web/src/).

## State split

Three layers, never mixed.

### Zustand — cross-panel app state

[`apps/web/src/store/app.ts`](../apps/web/src/store/app.ts). Persisted via Zustand middleware (localStorage).

Selected fields:

- `activeConnectionId` — UUID of the selected connection.
- `provider`, `model`, `ollamaBaseUrl` — LLM choices.
- `responseLocale` — language for NL explanations.
- `lastResponse` — most recent `Nl2SqlResponse`.
- `conversation` — `ChatTurn[]` for the ask flow.
- `highlightedTables`, `hoveredEntities` — visual highlights driven by NL2SQL `involvedEntities`.
- `theme` — `'light' | 'dark'`.
- `commandOpen`, `settingsOpen`, `historyOpen` — modal visibility.
- `schemaSearch` — sidebar search filter.
- `detailSelection` — `{ tableId, columnName? }` for the drawer.
- `graphView3D`, `resultView3D`, `graphDataMode` — view toggles.
- `leftCollapsed`, `rightCollapsed` — panel collapse.
- `autoExecute` — when true, auto-run the generated query.

### TanStack Query — server state

All HTTP calls go through TanStack Query. Cache keys are namespaced by resource and parameters:

```
['connections']
['connection', id]
['schema', connectionId, refresh]
['history', { connectionId, limit, offset, favoritesOnly }]
['ollama', 'models', baseUrl]
```

Mutations (`create`, `delete`, `nl2sql`, `execute`) invalidate the relevant keys narrowly. Optimistic updates are used for create/delete connection and favorite toggle.

### `useState` — purely local

Ephemeral component state (input focus, hover, animation flags). Never lifted unless another panel reads it.

## API client

[`apps/web/src/lib/api.ts`](../apps/web/src/lib/api.ts) wraps axios.

- Base URL is `/api` (Vite dev proxy: `5173 → 3001`).
- **Request interceptor** — adds `Authorization: Bearer <accessToken>` from in-memory token store, plus optional `X-API-Key` from `localStorage('dbview_api_key')`.
- **Response interceptor** — on 401, calls `POST /api/auth/refresh`, replaces the access token, retries the original request once. On a second 401, the user is sent to the login page.
- **Error shape** — extracts `code`, `message`, `issues` from the response body. Returned as a typed `DbviewApiError`.

Tokens **never** touch localStorage. The access token lives in a module-scope ref; the refresh token is in an httpOnly cookie set by the server.

## React Flow

The schema graph is laid out with `dagre`. Layout is memoized:

```ts
const layout = useMemo(
  () => layoutGraph(nodes, edges, direction),
  [nodes, edges, direction, highlightedTables],
);
```

Nodes are typed:

| `nodeType`       | Component            | Used for          |
| ---------------- | -------------------- | ----------------- |
| `tableNode`      | `TableNode.tsx`      | relational        |
| `labelNode`      | `LabelNode.tsx`      | graph             |
| `collectionNode` | `CollectionNode.tsx` | document / vector |
| `keyspaceNode`   | `KeyspaceNode.tsx`   | redis             |
| `indexNode`      | `IndexNode.tsx`      | elasticsearch     |
| `sObjectNode`    | `SObjectNode.tsx`    | salesforce        |

Each header uses a deterministic color derived from the schema name hash → palette index. Same schema always renders the same color.

## Theming

CSS custom properties drive the design tokens:

```
--surface-0   page background
--surface-1   panel background
--surface-2   raised surface
--text-fg
--text-muted
--accent       primary interactive color
--accent-fg    foreground on accent
--rose / --amber / --emerald   semantic
```

Never hex inline. Component classes (`.btn`, `.btn-primary`, `.input`, `.panel`) consolidate repeated utility stacks in `globals.css`.

Dark mode is the default. Light mode is a class on `<html>`.

## Keyboard

| Shortcut                          | Action                 |
| --------------------------------- | ---------------------- |
| `⌘K` / `Ctrl+K`                   | Open command palette   |
| `⌘↵` / `Ctrl+↵` (in Ask textarea) | Generate query         |
| `Esc`                             | Close palette / dialog |
| `Tab` order                       | Follows visual flow    |

All interactive elements have `focus:ring-2 focus:ring-accent`. All icon-only buttons have `aria-label`.

## Telemetry

[`apps/web/src/lib/observability.ts`](../apps/web/src/lib/observability.ts). Initialized once at module load, no-op unless `VITE_OTLP_ENDPOINT` is set. See [Observability](./observability.md#frontend-telemetry--grafana-faro) for details.
