from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4


CONTRACT_VERSION = "v0.experimental"
COMMANDS = frozenset({"start_upload", "cancel_upload", "scan_document", "get_status"})
JobStatus = Literal["accepted", "waiting_user", "running", "failed", "completed", "canceled"]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class CommandRequest:
    command_id: str
    command: str
    payload: dict[str, Any]
    contract_version: str = CONTRACT_VERSION
    requested_at: str = field(default_factory=utc_now)


@dataclass
class Job:
    job_id: str
    command_id: str
    command: str
    status: JobStatus = "accepted"
    created_at: str = field(default_factory=utc_now)
    updated_at: str = field(default_factory=utc_now)
    result: dict[str, Any] | None = None
    error: dict[str, str] | None = None

    @classmethod
    def for_request(cls, request: CommandRequest) -> "Job":
        return cls(job_id=str(uuid4()), command_id=request.command_id, command=request.command)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class CommandError(ValueError):
    code: str
    message: str

    def to_dict(self) -> dict[str, str]:
        return {"code": self.code, "message": self.message}
