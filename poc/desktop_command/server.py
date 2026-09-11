from __future__ import annotations

import argparse
import hmac
import os
import secrets
from typing import Any

from fastapi import FastAPI, Header, HTTPException, Request
import uvicorn

from .models import CommandError, CommandRequest
from .registry import CommandRegistry


def _require_bearer(authorization: str | None, token: str) -> None:
    prefix = "Bearer "
    supplied = authorization[len(prefix):] if authorization and authorization.startswith(prefix) else ""
    if not hmac.compare_digest(supplied, token):
        raise HTTPException(status_code=401, detail={"code": "unauthorized", "message": "Bearer token required"})


def _request_from_payload(payload: dict[str, Any]) -> CommandRequest:
    try:
        command_id = payload["command_id"]
        command = payload["command"]
    except KeyError as exc:
        raise CommandError("invalid_command", f"Missing field: {exc.args[0]}") from exc
    command_payload = payload.get("payload", {})
    if not isinstance(command_payload, dict):
        raise CommandError("invalid_command", "payload must be an object")
    return CommandRequest(
        command_id=str(command_id),
        command=str(command),
        payload=command_payload,
        contract_version=str(payload.get("contract_version", "")),
        requested_at=str(payload.get("requested_at", "")),
    )


def create_app(registry: CommandRegistry, *, token: str) -> FastAPI:
    if not token:
        raise ValueError("a non-empty sidecar token is required")
    app = FastAPI(title="DesktopCommand POC", docs_url=None, redoc_url=None, openapi_url=None)

    @app.get("/healthz")
    def healthz() -> dict[str, str]:
        return {"status": "ok", "contract_version": "v0.experimental"}

    @app.post("/v0/commands")
    async def submit_command(request: Request, authorization: str | None = Header(default=None)) -> dict[str, Any]:
        _require_bearer(authorization, token)
        try:
            body = await request.json()
            if not isinstance(body, dict):
                raise CommandError("invalid_command", "command request must be an object")
            job = registry.submit(_request_from_payload(body))
        except CommandError as exc:
            raise HTTPException(status_code=422, detail=exc.to_dict()) from exc
        return job.to_dict()

    @app.get("/v0/jobs/{job_id}")
    def get_job(job_id: str, authorization: str | None = Header(default=None)) -> dict[str, Any]:
        _require_bearer(authorization, token)
        job = registry.get(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail={"code": "job_not_found", "message": "Job was not found"})
        return job.to_dict()

    return app


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the isolated DesktopCommand POC sidecar")
    parser.add_argument("--port", type=int, required=True, help="explicit loopback port")
    parser.add_argument("--host", default="127.0.0.1", help="must remain loopback")
    parser.add_argument("--token", help="startup token; generated only for local manual POC use")
    args = parser.parse_args()
    if args.host != "127.0.0.1":
        parser.error("DesktopCommand POC binds only 127.0.0.1")
    token = args.token or os.environ.get("DESKTOP_COMMAND_TOKEN") or secrets.token_urlsafe(32)
    from .runtime import create_worker_backed_registry

    app = create_app(create_worker_backed_registry(os.getcwd())[0], token=token)
    uvicorn.run(app, host=args.host, port=args.port, log_level="warning", access_log=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
