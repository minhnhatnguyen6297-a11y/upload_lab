from __future__ import annotations

from collections.abc import Callable
import threading
from typing import Any

from .models import COMMANDS, CONTRACT_VERSION, CommandError, CommandRequest, Job, JobStatus, utc_now


_SENSITIVE_KEYS = frozenset({"credential", "cookie", "password", "access_token"})


def _contains_sensitive_payload(value: Any) -> bool:
    if isinstance(value, dict):
        return any(str(key).lower() in _SENSITIVE_KEYS or _contains_sensitive_payload(item) for key, item in value.items())
    if isinstance(value, (list, tuple)):
        return any(_contains_sensitive_payload(item) for item in value)
    return False


class CommandRegistry:
    """In-memory, idempotent command registry for the loopback POC only."""

    def __init__(self, enqueue: Callable[[str, dict[str, Any], str], None]):
        self._enqueue = enqueue
        self._jobs_by_id: dict[str, Job] = {}
        self._job_id_by_command_id: dict[str, str] = {}
        self._lock = threading.RLock()

    def submit(self, request: CommandRequest) -> Job:
        if request.contract_version != CONTRACT_VERSION:
            raise CommandError("unsupported_contract_version", "DesktopCommand version is unsupported")
        if request.command not in COMMANDS:
            raise CommandError("unknown_command", "DesktopCommand is not supported")
        if _contains_sensitive_payload(request.payload):
            raise CommandError("sensitive_payload_forbidden", "Sensitive payload fields are forbidden")
        with self._lock:
            if request.command == "get_status":
                job_id = request.payload.get("job_id")
                if not isinstance(job_id, str):
                    raise CommandError("invalid_command", "get_status requires payload.job_id")
                job = self._jobs_by_id.get(job_id)
                if job is None:
                    raise CommandError("job_not_found", "Job was not found")
                return job
            existing_job_id = self._job_id_by_command_id.get(request.command_id)
            if existing_job_id is not None:
                return self._jobs_by_id[existing_job_id]
            job = Job.for_request(request)
            self._jobs_by_id[job.job_id] = job
            self._job_id_by_command_id[request.command_id] = job.job_id
            self._enqueue(request.command, dict(request.payload), job.job_id)
            return job

    def get(self, job_id: str) -> Job | None:
        with self._lock:
            return self._jobs_by_id.get(job_id)

    def update(
        self,
        job_id: str,
        status: JobStatus,
        *,
        result: dict[str, Any] | None = None,
        error: dict[str, str] | None = None,
    ) -> Job | None:
        with self._lock:
            job = self._jobs_by_id.get(job_id)
            if job is None:
                return None
            job.status = status
            job.updated_at = utc_now()
            job.result = result
            job.error = error
            return job
