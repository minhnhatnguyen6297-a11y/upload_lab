from unittest.mock import Mock
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client() -> TestClient:
    from poc.desktop_command.registry import CommandRegistry
    from poc.desktop_command.server import create_app

    return TestClient(create_app(CommandRegistry(lambda *_: None), token="test-token"))


def command_payload(*, payload: dict | None = None) -> dict:
    return {
        "contract_version": "v0.experimental",
        "command_id": "command-1",
        "command": "scan_document",
        "payload": payload or {},
    }


def auth() -> dict[str, str]:
    return {"Authorization": "Bearer test-token"}


def test_command_endpoint_requires_bearer_token(client: TestClient) -> None:
    assert client.post("/v0/commands", json=command_payload()).status_code == 401


def test_cookie_payload_is_rejected_when_authenticated(client: TestClient) -> None:
    response = client.post("/v0/commands", headers=auth(), json=command_payload(payload={"cookie": "secret"}))

    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "sensitive_payload_forbidden"


def test_unknown_job_is_404_and_health_never_exposes_token(client: TestClient) -> None:
    assert client.get("/v0/jobs/nope", headers=auth()).status_code == 404
    assert "token" not in client.get("/healthz").text.lower()


def test_http_duplicate_returns_same_job_and_job_can_be_read(client: TestClient) -> None:
    first = client.post("/v0/commands", headers=auth(), json=command_payload())
    second = client.post("/v0/commands", headers=auth(), json=command_payload())

    assert first.status_code == second.status_code == 200
    assert first.json()["job_id"] == second.json()["job_id"]
    assert client.get(f"/v0/jobs/{first.json()['job_id']}", headers=auth()).json()["status"] == "accepted"


def test_nested_sensitive_payload_is_rejected() -> None:
    from poc.desktop_command.models import CommandError, CommandRequest
    from poc.desktop_command.registry import CommandRegistry

    with pytest.raises(CommandError, match="Sensitive"):
        CommandRegistry(lambda *_: None).submit(
            CommandRequest(command_id="c-sensitive", command="scan_document", payload={"nested": [{"cookie": "x"}]})
        )


def test_duplicate_command_returns_same_job_without_second_enqueue() -> None:
    from poc.desktop_command.models import CommandRequest
    from poc.desktop_command.registry import CommandRegistry

    enqueue = Mock()
    registry = CommandRegistry(enqueue)
    request = CommandRequest(command_id="c-1", command="scan_document", payload={})

    assert registry.submit(request).job_id == registry.submit(request).job_id
    assert enqueue.call_count == 1


def test_concurrent_duplicate_command_enqueues_once() -> None:
    from poc.desktop_command.models import CommandRequest
    from poc.desktop_command.registry import CommandRegistry

    enqueue = Mock()
    registry = CommandRegistry(enqueue)
    request = CommandRequest(command_id="c-race", command="scan_document", payload={})
    with ThreadPoolExecutor(max_workers=4) as executor:
        jobs = list(executor.map(lambda _: registry.submit(request), range(4)))

    assert {job.job_id for job in jobs}.__len__() == 1
    assert enqueue.call_count == 1


def test_start_upload_uses_public_slot_not_session() -> None:
    from poc.desktop_command.bridge import UploadWorkerBridge

    worker = Mock(spec=["start_login", "close_session"])
    bridge = UploadWorkerBridge(worker, scan_callback=Mock())

    bridge.submit("start_upload", {}, "job-1")

    worker.start_login.assert_called_once_with()


def test_cancel_closes_manual_login_through_public_slot() -> None:
    from poc.desktop_command.bridge import UploadWorkerBridge

    worker = Mock(spec=["start_login", "close_session"])
    bridge = UploadWorkerBridge(worker, scan_callback=Mock())

    bridge.submit("cancel_upload", {}, "job-1")

    worker.close_session.assert_called_once_with()


def test_bridge_reports_waiting_user_cancel_and_browser_error() -> None:
    from poc.desktop_command.bridge import UploadWorkerBridge

    worker = Mock(spec=["start_login", "close_session"])
    updates: list[tuple] = []
    bridge = UploadWorkerBridge(worker, scan_callback=Mock(), update_callback=lambda *update: updates.append(update))

    bridge.submit("start_upload", {}, "job-login")
    bridge._on_login_state({"status": "waiting"})
    bridge.submit("cancel_upload", {}, "job-cancel")
    bridge.submit("start_upload", {}, "job-login-2")
    bridge._on_failed("start_login", "browser unavailable")

    assert updates[0][1] == "waiting_user"
    assert updates[1][1] == "waiting_user"
    assert updates[2] == ("job-login", "canceled", None, None)
    assert updates[3] == ("job-cancel", "completed", {"canceled": True}, None)
    assert updates[5][1:] == ("failed", None, {"code": "browser_error", "message": "browser unavailable"})


def test_registry_and_bridge_keep_worker_ownership_with_waiting_user_status() -> None:
    from poc.desktop_command.bridge import UploadWorkerBridge
    from poc.desktop_command.models import CommandRequest
    from poc.desktop_command.registry import CommandRegistry

    worker = Mock(spec=["start_login", "close_session"])
    holder = {}
    registry = CommandRegistry(lambda command, payload, job_id: holder["bridge"].submit(command, payload, job_id))
    holder["bridge"] = UploadWorkerBridge(
        worker,
        scan_callback=Mock(),
        update_callback=lambda job_id, status, result, error: registry.update(
            job_id, status, result=result, error=error
        ),
    )

    job = registry.submit(CommandRequest(command_id="c-login", command="start_upload", payload={}))

    worker.start_login.assert_called_once_with()
    assert registry.get(job.job_id).status == "waiting_user"


def test_runtime_bridge_reports_scan_as_unconfigured_without_business_mapping(monkeypatch, tmp_path) -> None:
    from poc.desktop_command import runtime
    from poc.desktop_command.models import CommandRequest

    worker = Mock(spec=["start_login", "close_session"])
    monkeypatch.setattr(runtime, "UploadWorker", lambda working_dir: worker)
    registry, _bridge = runtime.create_worker_backed_registry(tmp_path)

    job = registry.submit(CommandRequest(command_id="c-scan", command="scan_document", payload={}))

    assert registry.get(job.job_id).status == "failed"
    assert registry.get(job.job_id).error["code"] == "scan_unavailable"


def test_get_status_command_returns_existing_job_without_enqueue() -> None:
    from poc.desktop_command.models import CommandRequest
    from poc.desktop_command.registry import CommandRegistry

    enqueue = Mock()
    registry = CommandRegistry(enqueue)
    job = registry.submit(CommandRequest(command_id="c-start", command="start_upload", payload={}))
    status = registry.submit(
        CommandRequest(command_id="c-status", command="get_status", payload={"job_id": job.job_id})
    )

    assert status.job_id == job.job_id
    assert enqueue.call_count == 1


def test_second_start_upload_is_rejected_without_replacing_active_job() -> None:
    from poc.desktop_command.bridge import UploadWorkerBridge

    worker = Mock(spec=["start_login", "close_session"])
    updates: list[tuple] = []
    bridge = UploadWorkerBridge(worker, scan_callback=Mock(), update_callback=lambda *update: updates.append(update))

    bridge.submit("start_upload", {}, "job-first")
    bridge.submit("start_upload", {}, "job-second")
    bridge._on_login_state({"status": "authenticated"})

    assert worker.start_login.call_count == 1
    assert updates[1][0:2] == ("job-second", "failed")
    assert updates[2][0:2] == ("job-first", "running")


def test_restart_loses_in_memory_job_without_reporting_completion() -> None:
    from poc.desktop_command.models import CommandRequest
    from poc.desktop_command.registry import CommandRegistry

    original = CommandRegistry(lambda *_: None)
    job = original.submit(CommandRequest(command_id="c-restart", command="start_upload", payload={}))
    restarted = CommandRegistry(lambda *_: None)

    assert restarted.get(job.job_id) is None
