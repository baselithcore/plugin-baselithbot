"""Kubernetes-Job-backed sandbox provider.

Dispatches every scanner invocation as a one-shot Kubernetes Job. Each
Job runs the scanner image with hardened pod-level guarantees that
mirror the local ``SandboxRunner`` baseline:

* ``readOnlyRootFilesystem: true``
* ``allowPrivilegeEscalation: false`` + ``runAsNonRoot: true``
* ``capabilities.drop: ["ALL"]``
* CPU + memory limits from :class:`RedAgentConfig`
* ``activeDeadlineSeconds`` enforces the operator's timeout server-side
  in addition to the asyncio-side wait
* Optional ``serviceAccountName`` bound to a least-privilege Role
* Network egress is meant to be governed by a cluster-wide
  ``NetworkPolicy`` keyed on the ``red-agent.baselith.io/sandbox=true``
  label; the policy itself is deployed by the operator (not by this
  module) and ``network=False`` adds an additional pod label
  ``red-agent.baselith.io/egress=deny`` so a stricter policy can drop
  egress entirely on those pods.

The provider is lazy-imported so red_agent stays loadable without the
``baselith-core[k8s]`` extra installed.
"""

from __future__ import annotations

import asyncio
import time
import uuid
from typing import TYPE_CHECKING, Any

from core.observability.logging import get_logger
from plugins.red_agent.sandbox_runner import SandboxResult

if TYPE_CHECKING:  # pragma: no cover
    pass

logger = get_logger(__name__)

_LABEL_PREFIX = "red-agent.baselith.io/"


class K8sSandboxUnavailable(RuntimeError):
    """Raised when ``kubernetes_asyncio`` is missing or the API call fails."""


class K8sJobSandbox:
    """One-Job-per-scanner Kubernetes sandbox provider."""

    def __init__(
        self,
        *,
        namespace: str,
        cpu_limit: str = "1",
        memory_limit: str = "1Gi",
        service_account: str | None = None,
        client_factory: Any | None = None,
    ) -> None:
        self.namespace = namespace
        self.cpu_limit = cpu_limit
        self.memory_limit = memory_limit
        self.service_account = service_account
        # Test seam: callers can inject a stubbed factory to avoid the
        # real ``kubernetes_asyncio.config.load_kube_config`` round-trip.
        self._client_factory = client_factory
        self._loaded = False

    async def execute(
        self,
        *,
        image: str,
        argv: list[str],
        timeout: int,
        network: bool,
        scanner: str,
        artifacts: list[str] | None = None,
    ) -> SandboxResult:
        del artifacts  # Job artifacts collected as logs; future: Volume mount
        client_mod = self._import_client()
        await self._ensure_config_loaded(client_mod)
        job_name = self._build_job_name(scanner)
        api_client = client_mod.api_client.ApiClient()
        try:
            batch_api = client_mod.BatchV1Api(api_client)
            core_api = client_mod.CoreV1Api(api_client)
            manifest = self._build_job_manifest(
                name=job_name,
                image=image,
                argv=argv,
                timeout=timeout,
                network=network,
                scanner=scanner,
            )
            started = time.monotonic()
            await batch_api.create_namespaced_job(
                namespace=self.namespace, body=manifest
            )
            try:
                exit_code = await self._wait_for_completion(
                    batch_api=batch_api, name=job_name, timeout=timeout
                )
                stdout, stderr = await self._collect_logs(
                    core_api=core_api, job_name=job_name
                )
            finally:
                await self._delete_job(batch_api=batch_api, name=job_name)
            duration = time.monotonic() - started
            return SandboxResult(
                exit_code=exit_code,
                stdout=stdout,
                stderr=stderr,
                duration_seconds=duration,
            )
        finally:
            await api_client.close()

    # --- internals ----------------------------------------------------

    def _import_client(self) -> Any:
        if self._client_factory is not None:
            return self._client_factory()
        try:
            import kubernetes_asyncio.client as client  # type: ignore[import-untyped]
            import kubernetes_asyncio.config as config  # type: ignore[import-untyped]
        except ImportError as exc:  # pragma: no cover — guarded by extras
            raise K8sSandboxUnavailable(
                "kubernetes_asyncio not installed; run "
                "'pip install baselith-core[k8s]' to enable the K8s "
                "sandbox provider"
            ) from exc
        client.config = config  # surface in one namespace for callers
        return client

    async def _ensure_config_loaded(self, client_mod: Any) -> None:
        if self._loaded:
            return
        try:
            await client_mod.config.load_incluster_config()
        except Exception:  # noqa: BLE001
            try:
                await client_mod.config.load_kube_config()
            except Exception as exc:  # noqa: BLE001
                raise K8sSandboxUnavailable(
                    f"failed to load kube config: {exc}"
                ) from exc
        self._loaded = True

    @staticmethod
    def _build_job_name(scanner: str) -> str:
        # K8s Job names: lowercase, dns-1123, ≤ 63 chars.
        suffix = uuid.uuid4().hex[:8]
        safe_scanner = scanner.replace("_", "-").lower()[:40]
        return f"red-agent-{safe_scanner}-{suffix}"

    def _build_job_manifest(
        self,
        *,
        name: str,
        image: str,
        argv: list[str],
        timeout: int,
        network: bool,
        scanner: str,
    ) -> dict[str, Any]:
        labels = {
            f"{_LABEL_PREFIX}sandbox": "true",
            f"{_LABEL_PREFIX}scanner": scanner.replace("_", "-"),
        }
        if not network:
            labels[f"{_LABEL_PREFIX}egress"] = "deny"
        pod_spec: dict[str, Any] = {
            "restartPolicy": "Never",
            "automountServiceAccountToken": False,
            "containers": [
                {
                    "name": "scanner",
                    "image": image,
                    "args": argv,
                    "resources": {
                        "limits": {
                            "cpu": self.cpu_limit,
                            "memory": self.memory_limit,
                        }
                    },
                    "securityContext": {
                        "runAsNonRoot": True,
                        "allowPrivilegeEscalation": False,
                        "readOnlyRootFilesystem": True,
                        "capabilities": {"drop": ["ALL"]},
                    },
                    "volumeMounts": [
                        {"name": "tmp", "mountPath": "/tmp"},  # nosec: B108
                        {"name": "workspace", "mountPath": "/workspace"},
                    ],
                }
            ],
            "volumes": [
                {"name": "tmp", "emptyDir": {"sizeLimit": "256Mi"}},
                {"name": "workspace", "emptyDir": {"sizeLimit": "1Gi"}},
            ],
        }
        if self.service_account:
            pod_spec["serviceAccountName"] = self.service_account
        return {
            "apiVersion": "batch/v1",
            "kind": "Job",
            "metadata": {
                "name": name,
                "namespace": self.namespace,
                "labels": labels,
            },
            "spec": {
                "ttlSecondsAfterFinished": 60,
                "backoffLimit": 0,
                "activeDeadlineSeconds": max(1, int(timeout)),
                "template": {
                    "metadata": {"labels": labels},
                    "spec": pod_spec,
                },
            },
        }

    async def _wait_for_completion(
        self, *, batch_api: Any, name: str, timeout: int
    ) -> int:
        deadline = time.monotonic() + timeout
        while True:
            if time.monotonic() > deadline:
                raise asyncio.TimeoutError(
                    f"K8s Job {name!r} did not complete within {timeout}s"
                )
            job = await batch_api.read_namespaced_job_status(
                name=name, namespace=self.namespace
            )
            status = getattr(job, "status", None)
            if status is None:
                await asyncio.sleep(1.0)
                continue
            if getattr(status, "succeeded", 0):
                return 0
            if getattr(status, "failed", 0):
                return 1
            await asyncio.sleep(1.0)

    async def _collect_logs(self, *, core_api: Any, job_name: str) -> tuple[str, str]:
        # Single-container Job → grab logs from the first matching pod.
        selector = f"job-name={job_name}"
        pods = await core_api.list_namespaced_pod(
            namespace=self.namespace, label_selector=selector
        )
        items = getattr(pods, "items", []) or []
        if not items:
            return "", ""
        pod_name = items[0].metadata.name
        try:
            stdout = await core_api.read_namespaced_pod_log(
                name=pod_name, namespace=self.namespace, container="scanner"
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "red_agent.k8s.log_read_failed",
                extra={"pod": pod_name, "err": str(exc)},
            )
            stdout = ""
        return stdout, ""

    async def _delete_job(self, *, batch_api: Any, name: str) -> None:
        try:
            await batch_api.delete_namespaced_job(
                name=name,
                namespace=self.namespace,
                propagation_policy="Background",
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "red_agent.k8s.job_delete_failed",
                extra={"name": name, "err": str(exc)},
            )
