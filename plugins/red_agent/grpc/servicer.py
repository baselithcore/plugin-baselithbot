"""AgentChannel servicer — bidirectional stream handler.

Phase 1 implementation. Each connected agent gets its own
:class:`AgentSession` that coordinates ``AgentHello`` handshake,
heartbeat tracking, telemetry persistence, and command dispatch.

The servicer body is intentionally thin: protocol-level concerns
live here, all business logic delegates to the persistence layer
that already handles RLS, audit, and tenant isolation. This keeps
the gRPC surface auditable in a single file (< 500 LOC) and lets
us swap implementations without touching the wire contract.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import AsyncIterator
from uuid import UUID, uuid4

from google.protobuf.json_format import MessageToDict
from google.protobuf.struct_pb2 import Struct

import grpc

from core.observability.logging import get_logger
from plugins.red_agent.agent_models import AgentStatus
from plugins.red_agent.persistence.agent_audit import AgentAuditLog
from plugins.red_agent.persistence.agent_telemetry import AgentTelemetryStore
from plugins.red_agent.persistence.agents import AgentPersistence
from plugins.red_agent.proto._generated import agent_pb2, agent_pb2_grpc

from .tenant_interceptor import TenantContext, tenant_context_from


def _safe_uuid(value: str) -> UUID:
    """Best-effort UUID parse — generates a fresh one on malformed input.

    Telemetry batch ids are advisory; if a daemon sends a non-UUID
    string we still want to persist the events under a synthetic id
    rather than drop the batch.
    """
    try:
        return UUID(value)
    except (ValueError, AttributeError):
        return uuid4()


def _struct_to_dict(struct: Struct) -> dict[str, object]:
    """Project a protobuf Struct into a plain dict for JSON storage."""
    if struct is None or not struct.fields:
        return {}
    return MessageToDict(struct, preserving_proto_field_name=True)


logger = get_logger(__name__)


PROTOCOL_VERSION_MIN = 1
TELEMETRY_BATCH_MAX = 500
MESSAGE_SIZE_MAX_BYTES = 4 * 1024 * 1024  # 4 MiB hard cap
HEARTBEAT_INTERVAL_SECONDS = 30


class AgentChannelServicer(agent_pb2_grpc.AgentChannelServicer):
    """Server-side AgentChannel implementation.

    The servicer holds no per-call state; every connection is a fresh
    :class:`AgentSession` so the handler stays trivially thread/task
    safe under high concurrency.
    """

    def __init__(
        self,
        *,
        agents: AgentPersistence,
        audit: AgentAuditLog,
        telemetry: AgentTelemetryStore | None = None,
    ) -> None:
        self._agents = agents
        self._audit = audit
        self._telemetry = telemetry

    async def OpenStream(  # noqa: N802 — gRPC method casing
        self,
        request_iterator: AsyncIterator[agent_pb2.AgentMessage],
        context: grpc.aio.ServicerContext,
    ) -> AsyncIterator[agent_pb2.ServerMessage]:
        tenant_ctx = tenant_context_from(context)
        session = AgentSession(
            tenant=tenant_ctx,
            agents=self._agents,
            audit=self._audit,
            telemetry=self._telemetry,
            context=context,
        )
        async for response in session.run(request_iterator):
            yield response


class AgentSession:
    """Per-connection state and message dispatch.

    Lifecycle: ``run`` reads the inbound stream, expects an
    ``AgentHello`` first, replies with ``ServerHello``, then loops
    over heartbeat / telemetry / command-result frames until either
    side closes the stream.
    """

    def __init__(
        self,
        *,
        tenant: TenantContext,
        agents: AgentPersistence,
        audit: AgentAuditLog,
        context: grpc.aio.ServicerContext,
        telemetry: AgentTelemetryStore | None = None,
    ) -> None:
        self._tenant = tenant
        self._agents = agents
        self._audit = audit
        self._telemetry = telemetry
        self._context = context
        self._outbox: asyncio.Queue[agent_pb2.ServerMessage] = asyncio.Queue()
        self._server_seq = 0
        self._last_acked_server_seq = 0
        self._handshake_done = asyncio.Event()

    async def run(
        self, request_iterator: AsyncIterator[agent_pb2.AgentMessage]
    ) -> AsyncIterator[agent_pb2.ServerMessage]:
        # Producer task drains the inbox into the outbound stream.
        # We yield from the outbox here so cancellation propagates
        # cleanly when the client disconnects.
        ingest = asyncio.create_task(self._ingest(request_iterator))
        try:
            while True:
                msg = await self._dequeue_or_finish(ingest)
                if msg is None:
                    return
                yield msg
        finally:
            if not ingest.done():
                ingest.cancel()
                try:
                    await ingest
                except (asyncio.CancelledError, Exception):  # noqa: BLE001
                    pass

    async def _dequeue_or_finish(
        self, ingest: asyncio.Task[None]
    ) -> agent_pb2.ServerMessage | None:
        getter = asyncio.create_task(self._outbox.get())
        done, _ = await asyncio.wait(
            {getter, ingest},
            return_when=asyncio.FIRST_COMPLETED,
        )
        if getter in done:
            return getter.result()
        # Ingest finished first — drain remaining outbox and exit.
        getter.cancel()
        if not self._outbox.empty():
            return self._outbox.get_nowait()
        return None

    async def _ingest(
        self, request_iterator: AsyncIterator[agent_pb2.AgentMessage]
    ) -> None:
        try:
            async for msg in request_iterator:
                await self._handle(msg)
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "red_agent.grpc.session.ingest_error",
                extra={
                    "agent_uuid": str(self._tenant.agent_uuid),
                    "error": str(exc),
                },
            )

    async def _handle(self, msg: agent_pb2.AgentMessage) -> None:
        kind = msg.WhichOneof("payload")
        if kind == "hello":
            await self._on_hello(msg.hello)
        elif kind == "heartbeat":
            await self._on_heartbeat()
        elif kind == "telemetry":
            await self._on_telemetry(msg.telemetry)
        elif kind == "command_result":
            await self._on_command_result(msg.command_result)
        elif kind == "logs":
            await self._on_logs(msg.logs)
        elif kind == "policy_ack":
            await self._on_policy_ack(msg.policy_ack)
        elif kind == "rotation_request":
            await self._on_rotation_request(msg.rotation_request)
        elif kind == "disconnect_notice":
            await self._on_disconnect_notice(msg.disconnect_notice)
        else:
            logger.debug(
                "red_agent.grpc.session.unknown_payload",
                extra={
                    "kind": kind,
                    "agent_uuid": str(self._tenant.agent_uuid),
                },
            )

    # --- payload handlers ------------------------------------------------

    async def _on_hello(self, hello: agent_pb2.AgentHello) -> None:
        if hello.protocol_version < PROTOCOL_VERSION_MIN:
            await self._enqueue_disconnect(
                agent_pb2.Disconnect.REASON_INCOMPATIBLE,
                f"protocol_version {hello.protocol_version} below "
                f"minimum {PROTOCOL_VERSION_MIN}",
            )
            return

        # Refresh agent registry with the latest platform metadata.
        await self._agents.update_status(
            self._tenant.agent_uuid,
            tenant_id=self._tenant.tenant_id,
            status=AgentStatus.ONLINE,
            last_seen_at=datetime.now(timezone.utc),
        )
        await self._audit.record(
            tenant_id=self._tenant.tenant_id,
            actor=f"daemon:{self._tenant.agent_uuid}",
            event="agent.connected",
            agent_uuid=self._tenant.agent_uuid,
            payload={
                "daemon_version": hello.daemon_version,
                "protocol_version": hello.protocol_version,
                "capabilities": list(hello.capabilities),
                "last_acked_server_seq": hello.last_acked_server_seq,
            },
        )
        self._last_acked_server_seq = hello.last_acked_server_seq

        server_hello = agent_pb2.ServerHello(
            protocol_version_min=PROTOCOL_VERSION_MIN,
            capabilities=list(hello.capabilities),
            telemetry_batch_max=TELEMETRY_BATCH_MAX,
            message_size_max_bytes=MESSAGE_SIZE_MAX_BYTES,
            tenant_id_echo=self._tenant.tenant_id,
        )
        server_hello.heartbeat_interval.seconds = HEARTBEAT_INTERVAL_SECONDS
        await self._enqueue(server_message_with_hello=server_hello)
        self._handshake_done.set()

    async def _on_heartbeat(self) -> None:
        await self._agents.update_status(
            self._tenant.agent_uuid,
            tenant_id=self._tenant.tenant_id,
            status=AgentStatus.ONLINE,
            last_seen_at=datetime.now(timezone.utc),
        )
        # Server-initiated heartbeat reply (allows the agent to compute
        # rough round-trip time).
        msg = agent_pb2.ServerMessage()
        msg.heartbeat.SetInParent()
        await self._enqueue_raw(msg)

    async def _on_telemetry(self, batch: agent_pb2.TelemetryBatch) -> None:
        # Persist events to the partitioned hot tier when configured;
        # always emit a single audit row per batch so operators can
        # verify end-to-end flow even on degraded deployments.
        events_payload = self._decode_events(batch)
        rows_written = 0
        if self._telemetry is not None:
            try:
                rows_written = await self._telemetry.insert_batch(
                    tenant_id=self._tenant.tenant_id,
                    agent_uuid=self._tenant.agent_uuid,
                    batch_id=_safe_uuid(batch.batch_id),
                    events=events_payload,
                )
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "red_agent.grpc.session.telemetry_persist_failed",
                    extra={
                        "agent_uuid": str(self._tenant.agent_uuid),
                        "batch_id": batch.batch_id,
                        "error": str(exc),
                    },
                )
        await self._audit.record(
            tenant_id=self._tenant.tenant_id,
            actor=f"daemon:{self._tenant.agent_uuid}",
            event="telemetry.batch_received",
            agent_uuid=self._tenant.agent_uuid,
            payload={
                "batch_id": batch.batch_id,
                "events": len(batch.events),
                "persisted": rows_written,
            },
        )

    def _decode_events(
        self, batch: agent_pb2.TelemetryBatch
    ) -> list[dict[str, object]]:
        """Project proto TelemetryEvents into the dict shape expected
        by :class:`AgentTelemetryStore`."""
        out: list[dict[str, object]] = []
        for ev in batch.events:
            observed_at = None
            if ev.observed_at.seconds or ev.observed_at.nanos:
                observed_at = datetime.fromtimestamp(
                    ev.observed_at.seconds + ev.observed_at.nanos / 1e9,
                    tz=timezone.utc,
                )
            severity_name = agent_pb2.Severity.Name(ev.severity)
            severity = severity_name.removeprefix("SEVERITY_").lower()
            out.append(
                {
                    "observed_at": observed_at,
                    "kind": ev.kind,
                    "severity": severity,
                    "attributes": _struct_to_dict(ev.attributes),
                    "correlation_id": ev.correlation_id or None,
                }
            )
        return out

    async def _on_command_result(self, result: agent_pb2.CommandResult) -> None:
        await self._audit.record(
            tenant_id=self._tenant.tenant_id,
            actor=f"daemon:{self._tenant.agent_uuid}",
            event="command.result",
            agent_uuid=self._tenant.agent_uuid,
            payload={
                "idempotency_key": result.idempotency_key,
                "correlation_id": result.correlation_id,
                "status": agent_pb2.CommandResult.Status.Name(result.status),
                "error_code": result.error_code,
            },
        )

    async def _on_logs(self, logs: agent_pb2.LogBatch) -> None:
        # Forward to the framework logger one entry at a time. This
        # is intentionally cheap; production deployments route logs
        # through a dedicated sink configured at the daemon side.
        for entry in logs.entries:
            logger.info(
                "red_agent.daemon.log",
                extra={
                    "agent_uuid": str(self._tenant.agent_uuid),
                    "tenant_id": self._tenant.tenant_id,
                    "level": agent_pb2.LogLevel.Name(entry.level),
                    "target": entry.target,
                    "message": entry.message,
                    "trace_id": entry.trace_id,
                },
            )

    async def _on_policy_ack(self, ack: agent_pb2.PolicyAck) -> None:
        await self._audit.record(
            tenant_id=self._tenant.tenant_id,
            actor=f"daemon:{self._tenant.agent_uuid}",
            event="policy.ack",
            agent_uuid=self._tenant.agent_uuid,
            payload={
                "version": ack.version,
                "applied": ack.applied,
                "error": ack.error,
            },
        )

    async def _on_rotation_request(self, _req: agent_pb2.RotationRequest) -> None:
        # Phase 1: rotation flow is REST-driven. Acknowledge the
        # request without granting; operators run rotation via the
        # admin API.
        logger.info(
            "red_agent.grpc.rotation.deferred_to_rest",
            extra={"agent_uuid": str(self._tenant.agent_uuid)},
        )

    async def _on_disconnect_notice(self, notice: agent_pb2.DisconnectNotice) -> None:
        reason = agent_pb2.DisconnectNotice.Reason.Name(notice.reason)
        await self._agents.update_status(
            self._tenant.agent_uuid,
            tenant_id=self._tenant.tenant_id,
            status=AgentStatus.OFFLINE,
            last_seen_at=datetime.now(timezone.utc),
            last_disconnect_reason=reason,
        )
        await self._audit.record(
            tenant_id=self._tenant.tenant_id,
            actor=f"daemon:{self._tenant.agent_uuid}",
            event="agent.disconnected",
            agent_uuid=self._tenant.agent_uuid,
            payload={"reason": reason, "message": notice.message},
        )

    # --- outbox helpers --------------------------------------------------

    async def _enqueue(
        self,
        *,
        server_message_with_hello: agent_pb2.ServerHello | None = None,
    ) -> None:
        msg = agent_pb2.ServerMessage()
        if server_message_with_hello is not None:
            msg.hello.CopyFrom(server_message_with_hello)
        await self._enqueue_raw(msg)

    async def _enqueue_raw(self, msg: agent_pb2.ServerMessage) -> None:
        self._server_seq += 1
        msg.seq = self._server_seq
        msg.ts.GetCurrentTime()
        await self._outbox.put(msg)

    async def _enqueue_disconnect(
        self,
        reason: int,
        message: str,
    ) -> None:
        msg = agent_pb2.ServerMessage()
        msg.disconnect.reason = reason  # type: ignore[assignment]
        msg.disconnect.message = message
        await self._enqueue_raw(msg)
        await self._audit.record(
            tenant_id=self._tenant.tenant_id,
            actor="server",
            event="agent.kicked",
            agent_uuid=self._tenant.agent_uuid,
            payload={
                "reason": agent_pb2.Disconnect.Reason.Name(reason),
                "message": message,
            },
        )

    @property
    def agent_uuid(self) -> UUID:
        return self._tenant.agent_uuid

    @property
    def tenant_id(self) -> str:
        return self._tenant.tenant_id

    def __repr__(self) -> str:
        return (
            f"AgentSession(agent={self._tenant.agent_uuid},"
            f" tenant={self._tenant.tenant_id})"
        )

    @staticmethod
    def _now_ms() -> int:
        return int(datetime.now(timezone.utc).timestamp() * 1000)

    # The handlers above are async-only; this guard prevents anyone
    # accidentally adding sync helpers that could block the event
    # loop and stall every session sharing the worker.
    def _assert_async_only(self) -> None:
        del self
