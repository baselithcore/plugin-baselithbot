# Module: services/events

In-process pub-sub per streaming WebSocket eventi pipeline. MVP single-process.

## Topology

```
agent.run() → emit_phase/emit_finding (services/agents/_emit.py)
                    ↓
     services.events.publish(doc_id, event)
                    ↓
            asyncio.Queue per subscriber
                    ↓
        WS handler (api/routes.py ws_analysis)
```

## API

- `publish(doc_id, event)` — async, broadcast a tutti i subscriber.
- `subscribe(doc_id)` — async context manager, restituisce `asyncio.Queue`.

## Event types

```ts
type Event =
  | { type: "phase",    phase: "started" | "structurer" | "legal" | "technical" | "pii" | "synthesizer" | "done" | "error" }
  | { type: "progress", current: number, total: number, label?: string }
  | { type: "finding",  finding: Finding }
  | { type: "trace",    step: ReasoningStep }
  | { type: "report",   report_id: string };
```

## Limiti MVP

- Single-process: subscribe e publish nello stesso processo Python.
- Multi-tenant post-MVP → swap a Redis pub/sub o NATS.
- Queue size cap 1024 → eventi droppati se subscriber lento (no backpressure to publisher).

## Frontend integration

Hook React: [useAnalysisStream.ts](../../docheck-ui/lib/useAnalysisStream.ts).
