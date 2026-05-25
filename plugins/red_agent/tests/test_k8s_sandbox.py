"""K8sJobSandbox tests using a stubbed kubernetes_asyncio client.

The real ``kubernetes_asyncio`` package is *not* required to run these
tests — :class:`K8sJobSandbox` accepts a ``client_factory`` callable
that returns a stand-in module exposing the same shape (``BatchV1Api``,
``CoreV1Api``, ``api_client.ApiClient``, ``config.load_*``).
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from plugins.red_agent.sandbox.k8s_job import K8sJobSandbox


class _ApiClientStub:
    async def close(self) -> None:
        return None


class _BatchV1ApiStub:
    def __init__(self, *, succeed_after: int = 1, fail: bool = False) -> None:
        self.created: list[dict[str, Any]] = []
        self.deleted: list[str] = []
        self._succeed_after = succeed_after
        self._fail = fail
        self._reads = 0

    async def create_namespaced_job(
        self, *, namespace: str, body: dict[str, Any]
    ) -> None:
        self.created.append({"namespace": namespace, "body": body})

    async def read_namespaced_job_status(self, *, name: str, namespace: str) -> Any:
        del namespace, name
        self._reads += 1
        if self._reads < self._succeed_after:
            return SimpleNamespace(status=SimpleNamespace(succeeded=0, failed=0))
        if self._fail:
            return SimpleNamespace(status=SimpleNamespace(succeeded=0, failed=1))
        return SimpleNamespace(status=SimpleNamespace(succeeded=1, failed=0))

    async def delete_namespaced_job(
        self, *, name: str, namespace: str, propagation_policy: str
    ) -> None:
        del namespace, propagation_policy
        self.deleted.append(name)


class _CoreV1ApiStub:
    def __init__(self, *, log_text: str = "scanner output") -> None:
        self.log_text = log_text

    async def list_namespaced_pod(self, *, namespace: str, label_selector: str) -> Any:
        del namespace, label_selector
        return SimpleNamespace(
            items=[SimpleNamespace(metadata=SimpleNamespace(name="pod-001"))]
        )

    async def read_namespaced_pod_log(
        self, *, name: str, namespace: str, container: str
    ) -> str:
        del name, namespace, container
        return self.log_text


def _client_factory(batch_api: _BatchV1ApiStub, core_api: _CoreV1ApiStub) -> Any:
    """Return a fake kubernetes_asyncio.client module."""
    api_client_ns = SimpleNamespace(ApiClient=_ApiClientStub)

    class _ConfigNs:
        @staticmethod
        async def load_incluster_config() -> None:
            return None

        @staticmethod
        async def load_kube_config() -> None:
            return None

    def _factory() -> Any:
        return SimpleNamespace(
            BatchV1Api=lambda _api: batch_api,
            CoreV1Api=lambda _api: core_api,
            api_client=api_client_ns,
            config=_ConfigNs(),
        )

    return _factory


@pytest.mark.asyncio
async def test_executes_and_returns_logs() -> None:
    batch = _BatchV1ApiStub(succeed_after=1)
    core = _CoreV1ApiStub(log_text="hello world")
    sandbox = K8sJobSandbox(
        namespace="red-agent",
        client_factory=_client_factory(batch, core),
    )
    result = await sandbox.execute(
        image="alpine:3",
        argv=["echo", "hi"],
        timeout=5,
        network=False,
        scanner="nmap",
    )
    assert result.exit_code == 0
    assert result.stdout == "hello world"
    assert len(batch.created) == 1
    assert batch.created[0]["namespace"] == "red-agent"
    assert batch.deleted == [batch.created[0]["body"]["metadata"]["name"]]


@pytest.mark.asyncio
async def test_failed_job_returns_nonzero_exit() -> None:
    batch = _BatchV1ApiStub(succeed_after=1, fail=True)
    core = _CoreV1ApiStub()
    sandbox = K8sJobSandbox(
        namespace="ra",
        client_factory=_client_factory(batch, core),
    )
    result = await sandbox.execute(
        image="alpine:3",
        argv=["false"],
        timeout=5,
        network=True,
        scanner="x",
    )
    assert result.exit_code == 1


@pytest.mark.asyncio
async def test_manifest_carries_hardened_security_context() -> None:
    batch = _BatchV1ApiStub(succeed_after=1)
    core = _CoreV1ApiStub()
    sandbox = K8sJobSandbox(
        namespace="ra",
        client_factory=_client_factory(batch, core),
    )
    await sandbox.execute(
        image="alpine:3",
        argv=["x"],
        timeout=5,
        network=False,
        scanner="trivy",
    )
    body = batch.created[0]["body"]
    spec = body["spec"]["template"]["spec"]
    container = spec["containers"][0]
    sec = container["securityContext"]
    assert sec["runAsNonRoot"] is True
    assert sec["readOnlyRootFilesystem"] is True
    assert sec["allowPrivilegeEscalation"] is False
    assert sec["capabilities"]["drop"] == ["ALL"]
    assert spec["automountServiceAccountToken"] is False
    assert body["spec"]["activeDeadlineSeconds"] == 5
    # network=False adds the egress=deny label
    labels = body["spec"]["template"]["metadata"]["labels"]
    assert labels["red-agent.baselith.io/egress"] == "deny"


@pytest.mark.asyncio
async def test_network_true_omits_deny_label() -> None:
    batch = _BatchV1ApiStub(succeed_after=1)
    core = _CoreV1ApiStub()
    sandbox = K8sJobSandbox(
        namespace="ra",
        client_factory=_client_factory(batch, core),
    )
    await sandbox.execute(
        image="alpine:3",
        argv=["x"],
        timeout=5,
        network=True,
        scanner="zap",
    )
    body = batch.created[0]["body"]
    labels = body["spec"]["template"]["metadata"]["labels"]
    assert "red-agent.baselith.io/egress" not in labels


@pytest.mark.asyncio
async def test_service_account_passed_through_when_set() -> None:
    batch = _BatchV1ApiStub(succeed_after=1)
    core = _CoreV1ApiStub()
    sandbox = K8sJobSandbox(
        namespace="ra",
        service_account="red-agent-scanner",
        client_factory=_client_factory(batch, core),
    )
    await sandbox.execute(
        image="alpine:3",
        argv=["x"],
        timeout=5,
        network=False,
        scanner="trivy",
    )
    spec = batch.created[0]["body"]["spec"]["template"]["spec"]
    assert spec["serviceAccountName"] == "red-agent-scanner"


@pytest.mark.asyncio
async def test_resource_limits_applied() -> None:
    batch = _BatchV1ApiStub(succeed_after=1)
    core = _CoreV1ApiStub()
    sandbox = K8sJobSandbox(
        namespace="ra",
        cpu_limit="500m",
        memory_limit="512Mi",
        client_factory=_client_factory(batch, core),
    )
    await sandbox.execute(
        image="alpine:3",
        argv=["x"],
        timeout=5,
        network=False,
        scanner="grype",
    )
    container = batch.created[0]["body"]["spec"]["template"]["spec"]["containers"][0]
    assert container["resources"]["limits"]["cpu"] == "500m"
    assert container["resources"]["limits"]["memory"] == "512Mi"


@pytest.mark.asyncio
async def test_protocol_compatibility() -> None:
    """Provider must satisfy the ``SandboxProtocol`` runtime check."""
    from plugins.red_agent.sandbox.protocol import SandboxProtocol

    batch = _BatchV1ApiStub(succeed_after=1)
    core = _CoreV1ApiStub()
    sandbox = K8sJobSandbox(
        namespace="ra",
        client_factory=_client_factory(batch, core),
    )
    assert isinstance(sandbox, SandboxProtocol)
